export type WalletConnectorType = "walletconnect";

export type WalletSessionSnapshot = {
  address: string | null;
  chainId: number | null;
  chainName: string | null;
  walletName: string | null;
  walletIcon: string | null;
  connectorType: WalletConnectorType | null;
  isConnected: boolean;
  isConnecting: boolean;
};

export interface WalletRuntime {
  connect(input: { walletId?: string }): Promise<{ uri: string }>;
  disconnect(): Promise<void>;
  restoreSession(): Promise<WalletSessionSnapshot | null>;
  subscribeSession(listener: (snapshot: WalletSessionSnapshot) => void): () => void;
  getEip1193Provider(): Promise<unknown>;
  switchToConfiguredChain(): Promise<void>;
  getConnectionMetadata(): { configError: string | null; availableConnectors: WalletConnectorType[] };
  awaitConnection(): Promise<WalletSessionSnapshot>;
}
