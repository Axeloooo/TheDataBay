export type WalletType = "evm" | "solana" | "btc" | string;

export type KeyReleaseRequest = {
  wallet_type: WalletType;
  address: string;
};

export type KeyReleaseResponse = {
  id: string;
  key_b64: string;
  nonce_b64: string;
  algorithm: string;
};
