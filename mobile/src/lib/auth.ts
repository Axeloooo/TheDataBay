import { ApiRequestError, apiRequest } from "@/src/lib/api";
import { useSessionStore, type AuthSession } from "@/src/stores/session-store";
import { useWalletStore } from "@/src/stores/wallet-store";

export type { AuthSession };

/** Re-sign when the token has less than this long left. */
export const SESSION_REFRESH_MARGIN_MS = 60_000;

export type NonceRequest = { wallet_type: "evm"; address: string };
export type NonceResponse = { nonce: string; message: string; expires_at: string };
export type VerifyRequest = NonceRequest & { nonce: string; signature: string };
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
  now?(): number;
};

function sameAddress(a: string, b: string): boolean {
  return a.toLowerCase() === b.toLowerCase();
}

export function createSessionClient(deps: SessionDeps) {
  const now = () => (deps.now ? deps.now() : Date.now());
  let inflight: Promise<string> | null = null;

  async function signIn(address: string): Promise<string> {
    const challenge = await deps.requestNonce({ wallet_type: "evm", address });
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
    const { getEvmProvider } = await import("@/src/lib/marketplace");
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
});

export const ensureSession = defaultClient.ensureSession;
export const withSession = defaultClient.withSession;

export function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}
