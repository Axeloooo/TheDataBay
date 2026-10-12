export type WalletMutationKind = "buy" | "create" | "connect" | null;

export type WalletConnectionSnapshot = {
  address: string | null;
  chainId: string | null;
  chainName: string | null;
  walletName: string | null;
  walletIcon: string | null;
  isConnected: boolean;
  isConnecting: boolean;
};

export type WalletTransactionSnapshot = {
  activeMutation: WalletMutationKind;
  transactionHash: string | null;
  transactionError: string | null;
};
