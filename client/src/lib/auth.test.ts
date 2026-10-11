import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiRequestError } from "@/lib/api";
import {
  createSessionClient,
  type AuthSession,
  type SessionDeps,
} from "@/lib/auth";

const ADDRESS = "0x00000000000000000000000000000000000000Aa";
const OTHER = "0x00000000000000000000000000000000000000bB";
const HOUR_MS = 60 * 60 * 1000;
const DOMAIN = "thedatabay.test";

function siweMessage(domain: string, address: string, nonce: string): string {
  return [
    `${domain} wants you to sign in with your Ethereum account:`,
    address,
    "",
    "Sign in to TheDataBay.",
    "",
    `URI: https://${domain}`,
    "Version: 1",
    "Chain ID: 31337",
    `Nonce: ${nonce}`,
  ].join("\n");
}

function makeDeps(start = 1_000_000) {
  let now = start;
  let address: string | null = ADDRESS;
  let session: AuthSession | null = null;
  let issued = 0;
  let tamper: ((message: string) => string) | null = null;

  const deps = {
    getAddress: vi.fn(() => address),
    signMessage: vi.fn(async (message: string) => `sig:${message}`),
    requestNonce: vi.fn(async (body: { address: string }) => {
      const nonce = `nonce${issued + 1}`;
      const message = siweMessage(DOMAIN, body.address, nonce);
      return {
        nonce,
        message: tamper ? tamper(message) : message,
        expires_at: new Date(now + 300_000).toISOString(),
      };
    }),
    verify: vi.fn(async (body: { address: string }) => {
      issued += 1;
      return {
        access_token: `token-${issued}`,
        token_type: "bearer",
        expires_at: new Date(now + HOUR_MS).toISOString(),
        wallet_type: "evm" as const,
        address: body.address,
      };
    }),
    getSession: () => session,
    setSession: vi.fn((next: AuthSession) => {
      session = next;
    }),
    clearSession: vi.fn(() => {
      session = null;
    }),
    now: () => now,
    expectedDomain: () => DOMAIN,
  } satisfies SessionDeps;

  return {
    deps,
    advance: (ms: number) => {
      now += ms;
    },
    setAddress: (next: string | null) => {
      address = next;
    },
    setTamper: (fn: (message: string) => string) => {
      tamper = fn;
    },
  };
}

describe("ensureSession", () => {
  let ctx: ReturnType<typeof makeDeps>;

  beforeEach(() => {
    ctx = makeDeps();
  });

  it("signs once for two consecutive calls", async () => {
    const { ensureSession } = createSessionClient(ctx.deps);

    const first = await ensureSession();
    const second = await ensureSession();

    expect(first).toBe("token-1");
    expect(second).toBe("token-1");
    expect(ctx.deps.signMessage).toHaveBeenCalledTimes(1);
  });

  it("shares one sign-in between concurrent calls", async () => {
    const { ensureSession } = createSessionClient(ctx.deps);

    const [a, b] = await Promise.all([ensureSession(), ensureSession()]);

    expect(a).toBe(b);
    expect(ctx.deps.signMessage).toHaveBeenCalledTimes(1);
  });

  it("verifies the server nonce with the wallet signature", async () => {
    const { ensureSession } = createSessionClient(ctx.deps);

    await ensureSession();

    expect(ctx.deps.requestNonce).toHaveBeenCalledWith({
      wallet_type: "evm",
      address: ADDRESS,
      scope: "user",
    });
    expect(ctx.deps.signMessage).toHaveBeenCalledWith(
      siweMessage(DOMAIN, ADDRESS, "nonce1"),
    );
    expect(ctx.deps.verify).toHaveBeenCalledWith({
      wallet_type: "evm",
      address: ADDRESS,
      nonce: "nonce1",
      signature: `sig:${siweMessage(DOMAIN, ADDRESS, "nonce1")}`,
    });
  });

  it("re-signs after the token expires", async () => {
    const { ensureSession } = createSessionClient(ctx.deps);
    await ensureSession();

    ctx.advance(HOUR_MS + 1);
    const token = await ensureSession();

    expect(token).toBe("token-2");
    expect(ctx.deps.signMessage).toHaveBeenCalledTimes(2);
  });

  it("re-signs when the token expires within 60 seconds", async () => {
    const { ensureSession } = createSessionClient(ctx.deps);
    await ensureSession();

    ctx.advance(HOUR_MS - 59_000);
    await ensureSession();

    expect(ctx.deps.signMessage).toHaveBeenCalledTimes(2);
  });

  it("re-signs when the connected wallet changes", async () => {
    const { ensureSession } = createSessionClient(ctx.deps);
    await ensureSession();

    ctx.setAddress(OTHER);
    await ensureSession();

    expect(ctx.deps.signMessage).toHaveBeenCalledTimes(2);
    expect(ctx.deps.verify).toHaveBeenLastCalledWith(
      expect.objectContaining({ address: OTHER }),
    );
  });

  it("rejects without a connected wallet", async () => {
    ctx.setAddress(null);
    const { ensureSession } = createSessionClient(ctx.deps);

    await expect(ensureSession()).rejects.toThrow(/connect/i);
    expect(ctx.deps.requestNonce).not.toHaveBeenCalled();
  });
});

describe("withSession", () => {
  it("signs in again and retries once when the API returns 401", async () => {
    const ctx = makeDeps();
    const { withSession } = createSessionClient(ctx.deps);
    const call = vi
      .fn<(token: string) => Promise<string>>()
      .mockRejectedValueOnce(new ApiRequestError("expired", 401))
      .mockResolvedValueOnce("ok");

    const result = await withSession(call);

    expect(result).toBe("ok");
    expect(call.mock.calls.map(([token]) => token)).toEqual([
      "token-1",
      "token-2",
    ]);
  });

  it("does not retry other errors", async () => {
    const ctx = makeDeps();
    const { withSession } = createSessionClient(ctx.deps);
    const call = vi.fn(async () => {
      throw new ApiRequestError("forbidden", 403);
    });

    await expect(withSession(call)).rejects.toThrow("forbidden");
    expect(call).toHaveBeenCalledTimes(1);
  });
});

describe("sign-in message checks", () => {
  it.each([
    ["another domain", (m: string) => m.replaceAll(DOMAIN, "evil.example")],
    ["another address", (m: string) => m.replace(ADDRESS, OTHER)],
    ["another nonce", (m: string) => m.replace("Nonce: nonce1", "Nonce: other")],
    ["a missing address line", (m: string) => m.replace(ADDRESS + "\n", "")],
  ])("refuses to sign a message for %s", async (_label, tamper) => {
    const ctx = makeDeps();
    ctx.setTamper(tamper);
    const { ensureSession } = createSessionClient(ctx.deps);

    await expect(ensureSession()).rejects.toThrow(/sign-in message/i);
    expect(ctx.deps.signMessage).not.toHaveBeenCalled();
    expect(ctx.deps.verify).not.toHaveBeenCalled();
  });

  it("accepts the connected address in a different letter case", async () => {
    const ctx = makeDeps();
    ctx.setTamper((m) => m.replace(ADDRESS, ADDRESS.toLowerCase()));
    const { ensureSession } = createSessionClient(ctx.deps);

    await expect(ensureSession()).resolves.toBe("token-1");
  });
});
