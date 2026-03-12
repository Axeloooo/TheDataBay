import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import { ensurePersistFormat } from "@/stores/persist-utils";

type WalletPersistedState = {
  address: string | null;
};

type EthereumRequestArgs = {
  method: string;
  params?: unknown[];
};

type EthereumProvider = {
  request: (args: EthereumRequestArgs) => Promise<unknown>;
  on?: (event: string, callback: (...args: unknown[]) => void) => void;
  removeListener?: (
    event: string,
    callback: (...args: unknown[]) => void,
  ) => void;
};

type WalletStore = {
  address: string | null;
  isConnected: boolean;
  connect: () => Promise<void>;
  disconnect: () => void;
  initWalletListeners: () => () => void;
};

const STORAGE_KEY = "bridgemart_wallet_address";

ensurePersistFormat<WalletPersistedState>(STORAGE_KEY, (raw) => {
  const normalized = raw.trim();
  return {
    address: normalized.length > 0 ? normalized : null,
  };
});

function getInjectedProvider(): EthereumProvider | null {
  if (typeof window === "undefined") return null;
  return (window.ethereum as EthereumProvider | undefined) ?? null;
}

function normalizeFirstAccount(accounts: unknown): string | null {
  if (!Array.isArray(accounts) || accounts.length === 0) {
    return null;
  }
  const first = accounts[0];
  return typeof first === "string" && first.length > 0 ? first : null;
}

export const useWalletStore = create<WalletStore>()(
  persist(
    (set) => ({
      address: null,
      isConnected: false,
      connect: async () => {
        const provider = getInjectedProvider();
        if (!provider) {
          alert(
            "No injected wallet found. Please install MetaMask (or a compatible wallet).",
          );
          return;
        }

        try {
          await provider.request({
            method: "wallet_requestPermissions",
            params: [{ eth_accounts: {} }],
          });
        } catch {
          // Some wallets do not support permissions API; continue.
        }

        const accounts = await provider.request({
          method: "eth_requestAccounts",
        });
        const next = normalizeFirstAccount(accounts);
        set({ address: next, isConnected: !!next });
      },
      disconnect: () => {
        set({ address: null, isConnected: false });
      },
      initWalletListeners: () => {
        const provider = getInjectedProvider();
        if (!provider?.on) {
          return () => undefined;
        }

        const handleAccountsChanged = (...args: unknown[]) => {
          const next = normalizeFirstAccount(args[0]);
          set({ address: next, isConnected: !!next });
        };

        const handleChainChanged = () => {
          // no-op for now; app logic can derive fresh state from chain-specific reads.
        };

        provider.on("accountsChanged", handleAccountsChanged);
        provider.on("chainChanged", handleChainChanged);

        return () => {
          provider.removeListener?.("accountsChanged", handleAccountsChanged);
          provider.removeListener?.("chainChanged", handleChainChanged);
        };
      },
    }),
    {
      name: STORAGE_KEY,
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        address: state.address,
      }),
      merge: (persisted, current) => {
        const next = {
          ...current,
          ...(persisted as Partial<WalletStore>),
        };
        return {
          ...next,
          isConnected: !!next.address,
        };
      },
    },
  ),
);
