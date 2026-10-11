export type WalletType = "evm" | "solana";

export type KeyReleaseResponse = {
  id: string;
  key_b64: string;
  nonce_b64: string;
  algorithm: string;
};
