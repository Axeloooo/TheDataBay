import Constants from "expo-constants";

function readExtra(name: string): string {
  const value = Constants.expoConfig?.extra?.[name];
  return typeof value === "string" ? value.trim() : "";
}

export const ENV = {
  API_URL: readExtra("apiUrl") || "http://localhost:8080",
  PINATA_GATEWAY_URL:
    readExtra("pinataGatewayUrl") || "https://gateway.pinata.cloud",
  WALLETCONNECT_PROJECT_ID: readExtra("walletConnectProjectId"),
  CONTRACT_ADDRESS: readExtra("contractAddress"),
  PAYMENT_TOKEN_ADDRESS: readExtra("paymentTokenAddress"),
  CADC_TOKEN_ADDRESS: readExtra("cadcTokenAddress"),
  CHAIN_ID: Number.parseInt(readExtra("chainId") || "31337", 10),
  RPC_URL: readExtra("rpcUrl") || "http://127.0.0.1:8545",
  EXPLORER_URL: readExtra("explorerUrl"),
} as const;

export function getMissingWalletConfig(): string[] {
  const missing: string[] = [];

  if (!ENV.WALLETCONNECT_PROJECT_ID) {
    missing.push("walletConnectProjectId");
  }
  if (!ENV.CONTRACT_ADDRESS) {
    missing.push("contractAddress");
  }
  if (!ENV.PAYMENT_TOKEN_ADDRESS) {
    missing.push("paymentTokenAddress");
  }
  if (!Number.isFinite(ENV.CHAIN_ID) || ENV.CHAIN_ID <= 0) {
    missing.push("chainId");
  }
  if (!ENV.RPC_URL) {
    missing.push("rpcUrl");
  }

  return missing;
}

export const WALLET_RUNTIME_CONFIGURED = getMissingWalletConfig().length === 0;
