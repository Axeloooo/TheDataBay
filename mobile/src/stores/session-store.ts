import { create } from "zustand";

export type AuthSession = {
  token: string;
  /** Token expiry as epoch milliseconds. */
  expiresAt: number;
  address: string;
  walletType: "evm";
};

type SessionStore = {
  session: AuthSession | null;
  setSession(session: AuthSession): void;
  clearSession(): void;
};

// Held in memory only: the short-lived token is never written to device storage,
// so a fresh app launch signs in again on the first protected call.
export const useSessionStore = create<SessionStore>()((set) => ({
  session: null,
  setSession: (session) => set({ session }),
  clearSession: () => set({ session: null }),
}));
