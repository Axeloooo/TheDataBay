import "@walletconnect/react-native-compat";
import "react-native-get-random-values";

import UniversalProvider from "@walletconnect/universal-provider";
import Constants from "expo-constants";

import { ENV, getMissingWalletConfig } from "@/constants/env";
import type { WalletConnectorType, WalletRuntime, WalletSessionSnapshot } from "./types";

const appScheme = Constants.expoConfig?.scheme ?? "mobile";

const CHAIN_NAMES: Record<number, string> = {
  1: "Ethereum",
  11155111: "Sepolia",
  31337: "Anvil",
};

function getChainName(chainId: number): string {
  return CHAIN_NAMES[chainId] ?? `Chain ${chainId}`;
}

function buildSnapshot(
  address: string | null,
  chainId: number | null,
  walletName: string | null,
  walletIcon: string | null,
  isConnected: boolean,
  isConnecting: boolean,
): WalletSessionSnapshot {
  return {
    address,
    chainId,
    chainName: chainId != null ? getChainName(chainId) : null,
    walletName,
    walletIcon,
    connectorType: isConnected ? "walletconnect" : null,
    isConnected,
    isConnecting,
  };
}

function parseAccountsFromSession(session: {
  namespaces?: { eip155?: { accounts?: string[] } };
}): { address: string | null; chainId: number | null } {
  const accounts = session.namespaces?.eip155?.accounts ?? [];
  const first = accounts[0];
  if (!first) {
    return { address: null, chainId: null };
  }
  const parts = first.split(":");
  const address = parts[2] ?? null;
  const chainId = parts[1] ? parseInt(parts[1], 10) : null;
  return { address, chainId };
}

function getPeerMeta(session: {
  peer?: { metadata?: { name?: string; icons?: string[] } };
}): { walletName: string | null; walletIcon: string | null } {
  const meta = session.peer?.metadata;
  return {
    walletName: meta?.name ?? null,
    walletIcon: meta?.icons?.[0] ?? null,
  };
}

// Singleton state
let providerInstance: UniversalProvider | null = null;
let initPromise: Promise<UniversalProvider> | null = null;
let pendingApproval: (() => Promise<unknown>) | null = null;

const listeners = new Set<(snapshot: WalletSessionSnapshot) => void>();

let currentSnapshot: WalletSessionSnapshot = buildSnapshot(
  null, null, null, null, false, false,
);

function notifyListeners(snapshot: WalletSessionSnapshot): void {
  currentSnapshot = snapshot;
  for (const listener of listeners) {
    listener(snapshot);
  }
}

function snapshotFromProvider(provider: UniversalProvider): WalletSessionSnapshot {
  if (!provider.session) {
    return buildSnapshot(null, null, null, null, false, false);
  }
  const { address, chainId } = parseAccountsFromSession(provider.session);
  const { walletName, walletIcon } = getPeerMeta(provider.session);
  return buildSnapshot(address, chainId, walletName, walletIcon, true, false);
}

async function getOrInitProvider(): Promise<UniversalProvider> {
  if (providerInstance) {
    return providerInstance;
  }

  if (initPromise) {
    return initPromise;
  }

  initPromise = UniversalProvider.init({
    projectId: ENV.WALLETCONNECT_PROJECT_ID,
    metadata: {
      name: "BridgeMart",
      description: "Decentralized dataset marketplace",
      url: "https://bridgemart.app",
      icons: ["https://bridgemart.app/icon.png"],
      redirect: { native: appScheme + "://" },
    },
  }).then((provider) => {
    providerInstance = provider;
    initPromise = null;

    provider.on("session_event", ({ event }: { event: { name: string; data: unknown }; chainId: string }) => {
      if (!providerInstance) return;
      if (event.name === "accountsChanged" || event.name === "chainChanged") {
        notifyListeners(snapshotFromProvider(providerInstance));
      }
    });

    provider.on("disconnect", () => {
      notifyListeners(buildSnapshot(null, null, null, null, false, false));
    });

    provider.on("session_update", ({ session }: { session: { namespaces?: { eip155?: { accounts?: string[] } }; peer?: { metadata?: { name?: string; icons?: string[] } } } }) => {
      if (!providerInstance) return;
      const { address, chainId } = parseAccountsFromSession(session);
      const { walletName, walletIcon } = getPeerMeta(session);
      notifyListeners(buildSnapshot(address, chainId, walletName, walletIcon, true, false));
    });

    return provider;
  });

  return initPromise;
}

const walletRuntimeImpl: WalletRuntime = {
  async connect(_input: { walletId?: string }): Promise<{ uri: string }> {
    const provider = await getOrInitProvider();

    const { uri, approval } = await provider.client.connect({
      requiredNamespaces: {
        eip155: {
          methods: [
            "eth_sendTransaction",
            "personal_sign",
            "eth_signTypedData_v4",
            "eth_sign",
          ],
          chains: [`eip155:${ENV.CHAIN_ID}`],
          events: ["chainChanged", "accountsChanged"],
        },
      },
    });

    if (!uri) {
      throw new Error("WalletConnect did not return a pairing URI.");
    }

    pendingApproval = approval;

    notifyListeners(buildSnapshot(null, null, null, null, false, true));

    return { uri };
  },

  async awaitConnection(): Promise<WalletSessionSnapshot> {
    if (!pendingApproval) {
      throw new Error("No pending WalletConnect connection to await.");
    }

    const approval = pendingApproval;
    pendingApproval = null;

    const session = (await approval()) as {
      namespaces?: { eip155?: { accounts?: string[] } };
      peer?: { metadata?: { name?: string; icons?: string[] } };
    };

    const { address, chainId } = parseAccountsFromSession(session);
    const { walletName, walletIcon } = getPeerMeta(session);
    const snapshot = buildSnapshot(address, chainId, walletName, walletIcon, true, false);

    notifyListeners(snapshot);

    return snapshot;
  },

  async disconnect(): Promise<void> {
    const provider = providerInstance;
    if (!provider) {
      notifyListeners(buildSnapshot(null, null, null, null, false, false));
      return;
    }

    try {
      if (provider.session?.topic) {
        const disconnect = provider.disconnect as (params?: {
          topic: string;
          reason: { code: number; message: string };
        }) => Promise<void>;
        await disconnect({
          topic: provider.session.topic,
          reason: { code: 6000, message: "User disconnected" },
        });
      }
    } catch {
      // Ignore disconnect errors — clear state regardless
    }

    pendingApproval = null;
    notifyListeners(buildSnapshot(null, null, null, null, false, false));
  },

  async restoreSession(): Promise<WalletSessionSnapshot | null> {
    const provider = await getOrInitProvider();

    if (provider.session) {
      const snapshot = snapshotFromProvider(provider);
      notifyListeners(snapshot);
      return snapshot;
    }

    return null;
  },

  subscribeSession(listener: (snapshot: WalletSessionSnapshot) => void): () => void {
    listeners.add(listener);
    // Immediately emit current state so subscriber is up to date
    listener(currentSnapshot);
    return () => {
      listeners.delete(listener);
    };
  },

  async getEip1193Provider(): Promise<unknown> {
    const provider = await getOrInitProvider();

    if (!provider.session) {
      throw new Error("No active WalletConnect session. Connect a wallet first.");
    }

    return provider;
  },

  async switchToConfiguredChain(): Promise<void> {
    const provider = await getOrInitProvider();

    if (!provider.session) {
      throw new Error("No active session.");
    }

    await provider.request({
      method: "wallet_switchEthereumChain",
      params: [{ chainId: `0x${ENV.CHAIN_ID.toString(16)}` }],
    });
  },

  getConnectionMetadata(): { configError: string | null; availableConnectors: WalletConnectorType[] } {
    const missing = getMissingWalletConfig();

    if (missing.length > 0) {
      return {
        configError: `WalletConnect is not configured. Missing Expo extra: ${missing.join(", ")}.`,
        availableConnectors: [],
      };
    }

    return {
      configError: null,
      availableConnectors: ["walletconnect"],
    };
  },
};

export const walletRuntime: WalletRuntime = walletRuntimeImpl;
