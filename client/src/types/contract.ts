import type { WalletType } from "@/types/dataset";

export type SettlementCurrency = "USDC";

export type MarketplaceDataItem = {
  id: string;
  title: string;
  description: string;
  seller: string;
  payment_token: string;
  price_atomic?: string;
  settlement_currency?: SettlementCurrency | (string & {});
  settlement_decimals?: number;
  /**
   * Legacy compatibility for pre-migration listings.
   * New code should read `price_atomic` plus settlement metadata.
   */
  price?: string | number | bigint;
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

export type PurchasedItemsRequest = {
  wallet_type: WalletType;
  address: string;
  start_block?: number | null;
  end_block?: number | null;
  limit?: number;
  offset?: number;
};

export type PurchasedItemsResponse = {
  wallet_id: string;
  items: MarketplaceDataItem[];
  count: number;
};
