import AsyncStorage from "@react-native-async-storage/async-storage";
import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

import { getAppKit, getWalletConfigError } from "@/src/lib/appkit";
import type {
  WalletConnectionSnapshot,
  WalletMutationKind,
  WalletTransactionSnapshot,
} from "@/src/types/wallet";

type WalletStore = WalletConnectionSnapshot &
  WalletTransactionSnapshot & {
    configError: string | null;
    openConnectModal: () => Promise<void>;
    disconnectWallet: () => Promise<void>;
    refreshSession: () => Promise<void>;
    syncConnection: (snapshot: WalletConnectionSnapshot) => void;
    setConnectionError: (message: string | null) => void;
    beginMutation: (kind: WalletMutationKind) => void;
    completeMutation: (hash: string | null) => void;
    failMutation: (message: string) => void;
    clearMutation: () => void;
  };

const STORAGE_KEY = "bridgemart_wallet_store_v2";

const initialConnection: WalletConnectionSnapshot = {
  address: null,
  chainId: null,
  chainName: null,
  walletName: null,
  walletIcon: null,
  isConnected: false,
  isConnecting: false,
};

const initialMutation: WalletTransactionSnapshot = {
  activeMutation: null,
  transactionHash: null,
  transactionError: null,
};

export const useWalletStore = create<WalletStore>()(
  persist(
    (set, get) => ({
      ...initialConnection,
      ...initialMutation,
      configError: getWalletConfigError(),

      async openConnectModal() {
        const configError = getWalletConfigError();

        if (configError) {
          set({ configError, transactionError: configError });
          return;
        }

        try {
          set({
            configError: null,
            isConnecting: true,
            activeMutation: "connect",
            transactionError: null,
          });
          getAppKit()?.open({ view: "Connect" });
        } catch (error) {
          set({
            isConnecting: false,
            activeMutation: null,
            transactionError:
              error instanceof Error
                ? error.message
                : "Failed to open wallet modal.",
          });
        }
      },

      async disconnectWallet() {
        try {
          await getAppKit()?.disconnect("eip155");
        } catch (error) {
          set({
            transactionError:
              error instanceof Error
                ? error.message
                : "Failed to disconnect wallet.",
          });
        } finally {
          set({
            ...initialConnection,
            ...initialMutation,
            configError: getWalletConfigError(),
          });
        }
      },

      async refreshSession() {
        set({ configError: getWalletConfigError() });
        if (!getAppKit()?.getProvider("eip155") && !get().isConnected) {
          set({ isConnecting: false, activeMutation: null });
        }
      },

      syncConnection(snapshot) {
        set({
          ...snapshot,
          configError: getWalletConfigError(),
          activeMutation:
            snapshot.isConnecting || get().activeMutation === "connect"
              ? "connect"
              : get().activeMutation,
          transactionError:
            snapshot.isConnected && get().activeMutation === "connect"
              ? null
              : get().transactionError,
        });

        if (!snapshot.isConnecting && get().activeMutation === "connect") {
          set({ activeMutation: null });
        }
      },

      setConnectionError(message) {
        set({ transactionError: message, configError: getWalletConfigError() });
      },

      beginMutation(kind) {
        set({
          activeMutation: kind,
          transactionError: null,
          transactionHash: null,
        });
      },

      completeMutation(hash) {
        set({
          activeMutation: null,
          transactionHash: hash,
          transactionError: null,
          isConnecting: false,
        });
      },

      failMutation(message) {
        set({
          activeMutation: null,
          transactionHash: null,
          transactionError: message,
          isConnecting: false,
        });
      },

      clearMutation() {
        set({ ...initialMutation, configError: getWalletConfigError() });
      },
    }),
    {
      name: STORAGE_KEY,
      storage: createJSONStorage(() => AsyncStorage),
      partialize: (state) => ({
        address: state.address,
        chainId: state.chainId,
        chainName: state.chainName,
        walletName: state.walletName,
        walletIcon: state.walletIcon,
      }),
    },
  ),
);
