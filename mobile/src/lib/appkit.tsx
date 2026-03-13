import "@walletconnect/react-native-compat";
import "react-native-get-random-values";

import { EthersAdapter } from "@reown/appkit-ethers-react-native";
import {
  AppKitProvider,
  AppKit as AppKitModal,
  createAppKit,
} from "@reown/appkit-react-native";
import type { Network } from "@reown/appkit-common-react-native";
import Constants from "expo-constants";
import React from "react";

import {
  ENV,
  WALLET_RUNTIME_CONFIGURED,
  getMissingWalletConfig,
} from "@/constants/env";
import { appKitStorage } from "@/src/lib/appkit-storage";

const appName = Constants.expoConfig?.name ?? "BridgeMart";
const appScheme = Constants.expoConfig?.scheme ?? "mobile";

export const SUPPORTED_EVM_NETWORK: Network = {
  id: ENV.CHAIN_ID,
  name:
    ENV.CHAIN_ID === 1
      ? "Ethereum"
      : ENV.CHAIN_ID === 11155111
        ? "Sepolia"
        : "BridgeMart Localnet",
  nativeCurrency: {
    name: "Ether",
    symbol: "ETH",
    decimals: 18,
  },
  rpcUrls: {
    default: {
      http: [ENV.RPC_URL],
    },
  },
  blockExplorers: ENV.EXPLORER_URL
    ? {
        default: {
          name: "Explorer",
          url: ENV.EXPLORER_URL,
        },
      }
    : undefined,
  chainNamespace: "eip155",
  caipNetworkId: `eip155:${ENV.CHAIN_ID}`,
  testnet: ENV.CHAIN_ID !== 1,
};

let appKitInstance: ReturnType<typeof createAppKit> | null = null;
let appKitInitError: string | null = null;

function canInitializeWalletRuntime(): boolean {
  // Expo web does a server render pass where browser globals are unavailable.
  return typeof window !== "undefined";
}

export function getAppKit(): ReturnType<typeof createAppKit> | null {
  if (!canInitializeWalletRuntime()) {
    return null;
  }

  if (!WALLET_RUNTIME_CONFIGURED) {
    return null;
  }

  if (appKitInitError) {
    return null;
  }

  if (appKitInstance) {
    return appKitInstance;
  }

  try {
    appKitInstance = createAppKit({
      projectId: ENV.WALLETCONNECT_PROJECT_ID,
      metadata: {
        name: appName,
        description: "BridgeMart decentralized dataset marketplace",
        url: "https://bridgemart.app",
        icons: ["https://bridgemart.app/icon.png"],
        redirect: {
          native: appScheme + "://",
        },
      },
      adapters: [new EthersAdapter()],
      networks: [SUPPORTED_EVM_NETWORK],
      defaultNetwork: SUPPORTED_EVM_NETWORK,
      storage: appKitStorage,
      enableAnalytics: false,
    });
  } catch (error) {
    appKitInitError =
      error instanceof Error ? error.message : "Unknown AppKit init error";
    console.error("AppKit initialization failed:", error);
    return null;
  }

  return appKitInstance;
}

export function getWalletConfigError(): string | null {
  const missing = getMissingWalletConfig();

  if (missing.length === 0) {
    return appKitInitError
      ? "Wallet runtime initialization failed: " + appKitInitError
      : null;
  }

  return `WalletConnect is not configured. Missing Expo extra: ${missing.join(", ")}.`;
}

type WalletAppKitProviderProps = {
  children: React.ReactNode;
  sync: React.ReactNode;
};

export function WalletAppKitProvider({
  children,
  sync,
}: WalletAppKitProviderProps) {
  const instance = getAppKit();

  if (!instance) {
    return <>{children}</>;
  }

  return (
    <AppKitProvider instance={instance}>
      {children}
      {sync}
      <AppKitModal />
    </AppKitProvider>
  );
}
