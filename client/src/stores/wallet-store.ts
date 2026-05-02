import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import { walletRuntime } from "@/lib/wallet/runtime";
import type {
  WalletConnectorType,
  WalletSessionSnapshot,
} from "@/lib/wallet/types";

export type WalletMutationKind = "buy" | "create" | "connect" | null;

type WalletStore = WalletSessionSnapshot & {
  configError: string | null;
  activeMutation: WalletMutationKind;
  transactionHash: string | null;
  transactionError: string | null;
  userDisconnected: boolean;
  connect(
    connector: WalletConnectorType,
    eip6963Provider?: object,
  ): Promise<void>;
  disconnect(): Promise<void>;
  restoreSession(): Promise<void>;
  subscribeToRuntime(): () => void;
  beginMutation(kind: WalletMutationKind): void;
  completeMutation(hash: string | null): void;
  failMutation(message: string): void;
  clearMutation(): void;
};

type WalletPersistedState = {
  address: string | null;
  userDisconnected: boolean;
};

const STORAGE_KEY = "thedatabay_wallet_v4";

export const useWalletStore = create<WalletStore>()(
  persist(
    (set) => ({
      // WalletSessionSnapshot defaults
      address: null,
      chainId: null,
      chainName: null,
      walletName: null,
      walletIcon: null,
      connectorType: null,
      isConnected: false,
      isConnecting: false,
      // Extra store state
      configError: null,
      activeMutation: null,
      transactionHash: null,
      transactionError: null,
      userDisconnected: false,

      connect: async (
        connector: WalletConnectorType,
        eip6963Provider?: object,
      ) => {
        set({ userDisconnected: false, isConnecting: true });
        try {
          await walletRuntime.connect({ connector, eip6963Provider });
        } finally {
          set({ isConnecting: false });
        }
      },

      disconnect: async () => {
        // Persist the disconnected state synchronously BEFORE any async work.
        // If the user closes/refreshes the tab during the WalletConnect network
        // call, localStorage will already reflect userDisconnected: true and the
        // cleared address, preventing auto-reconnect on the next page load.
        set({
          address: null,
          chainId: null,
          chainName: null,
          walletName: null,
          walletIcon: null,
          connectorType: null,
          isConnected: false,
          isConnecting: false,
          userDisconnected: true,
        });
        await walletRuntime.disconnect();
      },

      restoreSession: async () => {
        if (useWalletStore.getState().userDisconnected) {
          return;
        }
        const snapshot = await walletRuntime.restoreSession();
        if (snapshot) {
          set(snapshot);
        }
      },

      subscribeToRuntime: () => {
        const { configError } = walletRuntime.getConnectionMetadata();
        set({ configError });
        const unsubscribe = walletRuntime.subscribeSession(
          (snap: WalletSessionSnapshot) => {
            set(snap);
          },
        );
        return unsubscribe;
      },

      beginMutation: (kind: WalletMutationKind) => {
        set({
          activeMutation: kind,
          transactionHash: null,
          transactionError: null,
        });
      },

      completeMutation: (hash: string | null) => {
        set({
          activeMutation: null,
          transactionHash: hash,
          transactionError: null,
        });
      },

      failMutation: (message: string) => {
        set({
          activeMutation: null,
          transactionHash: null,
          transactionError: message,
        });
      },

      clearMutation: () => {
        set({
          activeMutation: null,
          transactionHash: null,
          transactionError: null,
        });
      },
    }),
    {
      name: STORAGE_KEY,
      storage: createJSONStorage(() => localStorage),
      partialize: (state): WalletPersistedState => ({
        address: state.address,
        userDisconnected: state.userDisconnected,
      }),
      merge: (persisted, current) => {
        const p = persisted as Partial<WalletStore>;
        return {
          ...current,
          address: p.address ?? null,
          userDisconnected: p.userDisconnected ?? false,
          isConnected: !!p.address,
        };
      },
    },
  ),
);
