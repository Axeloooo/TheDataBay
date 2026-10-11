export type MeSource = "indexer" | "contract";

export type PurchasedListing = {
  listing_id: string;
  title: string;
  description: string;
  dataset_url: string;
  price_paid: string;
  payment_token: string;
  token_symbol: string;
  token_decimals: number;
  purchased_at: string | null;
  source: MeSource;
};

export type SellerListing = {
  listing_id: string;
  title: string;
  price: string;
  payment_token: string;
  token_symbol: string;
  token_decimals: number;
  sales_count: number;
  earnings_by_token: Record<string, string>;
  price_editable: boolean;
  source: MeSource;
};
