export type WalletConnectorType = "walletconnect" | "injected";

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
  connect(input: { connector: WalletConnectorType; eip6963Provider?: object }): Promise<void>;
  disconnect(): Promise<void>;
  restoreSession(): Promise<WalletSessionSnapshot | null>;
  subscribeSession(listener: (snapshot: WalletSessionSnapshot) => void): () => void;
  getEip1193Provider(): Promise<unknown>;
  switchToConfiguredChain(): Promise<void>;
  getConnectionMetadata(): { configError: string | null; availableConnectors: WalletConnectorType[] };
}
