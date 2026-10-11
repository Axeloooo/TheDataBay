import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

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

const STORAGE_KEY = "thedatabay_session_v1";

// Kept in sessionStorage (not localStorage) so the short-lived token does not
// outlive the browser tab.
export const useSessionStore = create<SessionStore>()(
  persist(
    (set) => ({
      session: null,
      setSession: (session) => set({ session }),
      clearSession: () => set({ session: null }),
    }),
    {
      name: STORAGE_KEY,
      storage: createJSONStorage(() => sessionStorage),
      partialize: (state) => ({ session: state.session }),
    },
  ),
);
