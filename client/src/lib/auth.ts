import { ApiRequestError, apiRequest } from "@/lib/api";
import { useSessionStore, type AuthSession } from "@/stores/session-store";
import { useWalletStore } from "@/stores/wallet-store";

export type { AuthSession };

/** Re-sign when the token has less than this long left. */
export const SESSION_REFRESH_MARGIN_MS = 60_000;

export type NonceRequest = {
  wallet_type: "evm";
  address: string;
  scope: "user";
};
export type NonceResponse = { nonce: string; message: string; expires_at: string };
export type VerifyRequest = Omit<NonceRequest, "scope"> & {
  nonce: string;
  signature: string;
};
export type TokenResponse = {
  access_token: string;
  token_type: string;
  expires_at: string;
  wallet_type: "evm" | "solana";
  address: string;
};

export type SessionDeps = {
  getAddress(): string | null;
  signMessage(message: string): Promise<string>;
  requestNonce(body: NonceRequest): Promise<NonceResponse>;
  verify(body: VerifyRequest): Promise<TokenResponse>;
  getSession(): AuthSession | null;
  setSession(session: AuthSession): void;
  clearSession(): void;
  /** Host the API names in the sign-in message (its AUTH_DOMAIN). */
  expectedDomain(): string;
  now?(): number;
};

/** EVM addresses compare case-insensitively (mixed case is only a checksum). */
export function sameAddress(a: string, b: string): boolean {
  return a.toLowerCase() === b.toLowerCase();
}

/**
 * Refuse to sign unless the server's message is for this app's domain, the
 * connected wallet and the issued nonce, so a hostile or misconfigured API
 * cannot get a signature for another site or account.
 */
export function assertSignInMessage(
  message: string,
  expected: { domain: string; address: string; nonce: string },
): void {
  const lines = message.split("\n");
  const ok =
    expected.domain.length > 0 &&
    lines[0] ===
      `${expected.domain} wants you to sign in with your Ethereum account:` &&
    typeof lines[1] === "string" &&
    sameAddress(lines[1], expected.address) &&
    lines.includes(`URI: https://${expected.domain}`) &&
    lines.includes(`Nonce: ${expected.nonce}`);
  if (!ok) {
    throw new Error(
      "Refusing to sign: the sign-in message does not match this app and wallet.",
    );
  }
}

export function createSessionClient(deps: SessionDeps) {
  const now = () => (deps.now ? deps.now() : Date.now());
  let inflight: Promise<string> | null = null;

  async function signIn(address: string): Promise<string> {
    const challenge = await deps.requestNonce({
      wallet_type: "evm",
      address,
      scope: "user",
    });
    assertSignInMessage(challenge.message, {
      domain: deps.expectedDomain(),
      address,
      nonce: challenge.nonce,
    });
    const signature = await deps.signMessage(challenge.message);
    const result = await deps.verify({
      wallet_type: "evm",
      address,
      nonce: challenge.nonce,
      signature,
    });
    deps.setSession({
      token: result.access_token,
      expiresAt: Date.parse(result.expires_at),
      address: result.address,
      walletType: "evm",
    });
    return result.access_token;
  }

  /**
   * Return a valid bearer token, prompting the connected wallet to sign in only
   * when there is no token, it belongs to another wallet, or it expires within
   * SESSION_REFRESH_MARGIN_MS.
   */
  async function ensureSession(): Promise<string> {
    const address = deps.getAddress();
    if (!address) {
      throw new Error("Connect your wallet to sign in.");
    }

    const session = deps.getSession();
    if (
      session &&
      sameAddress(session.address, address) &&
      session.expiresAt - now() > SESSION_REFRESH_MARGIN_MS
    ) {
      return session.token;
    }

    if (!inflight) {
      inflight = signIn(address).finally(() => {
        inflight = null;
      });
    }
    return inflight;
  }

  /** Run an authenticated call; on 401, sign in again and retry once. */
  async function withSession<T>(call: (token: string) => Promise<T>): Promise<T> {
    const token = await ensureSession();
    try {
      return await call(token);
    } catch (error) {
      if (error instanceof ApiRequestError && error.status === 401) {
        deps.clearSession();
        return call(await ensureSession());
      }
      throw error;
    }
  }

  return { ensureSession, withSession };
}

const defaultClient = createSessionClient({
  getAddress: () => useWalletStore.getState().address,
  signMessage: async (message) => {
    const { getEvmProvider } = await import("@/lib/marketplace");
    const provider = await getEvmProvider();
    const signer = await provider.getSigner();
    return signer.signMessage(message);
  },
  requestNonce: (body) =>
    apiRequest<NonceResponse>("/api/v1/auth/nonce", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  verify: (body) =>
    apiRequest<TokenResponse>("/api/v1/auth/verify", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getSession: () => useSessionStore.getState().session,
  setSession: (session) => useSessionStore.getState().setSession(session),
  clearSession: () => useSessionStore.getState().clearSession(),
  // AUTH_DOMAIN when set at build time, otherwise the host serving this app.
  expectedDomain: () =>
    (import.meta.env.VITE_AUTH_DOMAIN as string | undefined)?.trim() ||
    window.location.host,
});

export const ensureSession = defaultClient.ensureSession;
export const withSession = defaultClient.withSession;

export function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}
