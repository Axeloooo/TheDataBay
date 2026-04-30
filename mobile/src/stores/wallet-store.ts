import AsyncStorage from "@react-native-async-storage/async-storage";
import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

import { walletRuntime } from "@/src/lib/wallet/runtime";
import type { WalletSessionSnapshot } from "@/src/lib/wallet/types";
import type {
  WalletConnectionSnapshot,
  WalletMutationKind,
  WalletTransactionSnapshot,
} from "@/src/types/wallet";

type WalletStore = WalletConnectionSnapshot &
  WalletTransactionSnapshot & {
    configError: string | null;
    pendingWcUri: string | null;
    openConnectModal: () => Promise<void>;
    disconnectWallet: () => Promise<void>;
    refreshSession: () => Promise<void>;
    syncConnection: (snapshot: WalletConnectionSnapshot) => void;
    setConnectionError: (message: string | null) => void;
    beginMutation: (kind: WalletMutationKind) => void;
    completeMutation: (hash: string | null) => void;
    failMutation: (message: string) => void;
    clearMutation: () => void;
    clearPendingUri: () => void;
    subscribeToRuntime: () => () => void;
  };

const STORAGE_KEY = "ulenor_wallet_store_v2";

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

function snapshotToConnection(snap: WalletSessionSnapshot): WalletConnectionSnapshot {
  return {
    address: snap.address,
    chainId: snap.chainId != null ? String(snap.chainId) : null,
    chainName: snap.chainName,
    walletName: snap.walletName,
    walletIcon: snap.walletIcon,
    isConnected: snap.isConnected,
    isConnecting: snap.isConnecting,
  };
}

export const useWalletStore = create<WalletStore>()(
  persist(
    (set, get) => ({
      ...initialConnection,
      ...initialMutation,
      configError: walletRuntime.getConnectionMetadata().configError,
      pendingWcUri: null,

      async openConnectModal() {
        const { configError } = walletRuntime.getConnectionMetadata();

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

          const { uri } = await walletRuntime.connect({});
          set({ pendingWcUri: uri });
        } catch (error) {
          set({
            isConnecting: false,
            activeMutation: null,
            pendingWcUri: null,
            transactionError:
              error instanceof Error
                ? error.message
                : "Failed to initiate wallet connection.",
          });
        }
      },

      async disconnectWallet() {
        try {
          await walletRuntime.disconnect();
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
            pendingWcUri: null,
            configError: walletRuntime.getConnectionMetadata().configError,
          });
        }
      },

      async refreshSession() {
        const { configError } = walletRuntime.getConnectionMetadata();
        set({ configError });

        try {
          const snapshot = await walletRuntime.restoreSession();

          if (snapshot) {
            const connection = snapshotToConnection(snapshot);
            set({
              ...connection,
              configError: walletRuntime.getConnectionMetadata().configError,
            });
          } else if (!get().isConnected) {
            set({ isConnecting: false, activeMutation: null });
          }
        } catch {
          set({ isConnecting: false, activeMutation: null });
        }
      },

      syncConnection(snapshot) {
        set({
          ...snapshot,
          configError: walletRuntime.getConnectionMetadata().configError,
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
        set({
          transactionError: message,
          configError: walletRuntime.getConnectionMetadata().configError,
        });
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
        set({
          ...initialMutation,
          configError: walletRuntime.getConnectionMetadata().configError,
        });
      },

      clearPendingUri() {
        set({ pendingWcUri: null });
      },

      subscribeToRuntime() {
        const unsubscribe = walletRuntime.subscribeSession((snap) => {
          const connection = snapshotToConnection(snap);
          get().syncConnection(connection);

          // Clear pending URI when connection is established
          if (snap.isConnected && get().pendingWcUri) {
            set({ pendingWcUri: null });
          }
        });
        return unsubscribe;
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
