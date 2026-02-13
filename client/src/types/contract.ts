import type { WalletType } from "@/types/dataset";

export type MarketplaceDataItem = {
  id: string;
  title: string;
  description: string;
  seller: string;
  price: number;
  dataset_url: string;
  dataset_hash: string;
  signature_url: string;
  signature_hash: string;
  exists: boolean;
  purchase_count: number;
};

export type WalletAccessRequest = {
  wallet_type: WalletType;
  address: string;
};

export type AccessCheckResponse = {
  has_access: boolean;
};
