export type ScoreLabel = "high" | "moderate" | "low";

export type SimilaritySearchRequest = {
  query: string;
  limit?: number;
};

/** Flat ranked dataset item from the backend similarity-search endpoint. */
export type RankedDataset = {
  listing_id: string;
  title: string;
  description: string;
  seller: string;
  payment_token: string;
  price_atomic: number;
  settlement_currency: string;
  settlement_decimals: number;
  purchase_count: number;
  score: number;
  score_label: ScoreLabel;
};

export type SimilaritySearchResponse = {
  query: string;
  results: RankedDataset[];
  count: number;
};

/** Minimal dataset fields that RecordCard needs. */
export type CardDataset = {
  id: string;
  title: string;
  description: string;
  payment_token?: string;
  price_atomic?: string;
  price?: string | number | bigint;
  settlement_currency?: string;
  settlement_decimals?: number;
  purchase_count?: number;
};

/** View model passed to RecordCard — score fields absent for browse mode. */
export type CardViewModel = {
  dataset: CardDataset;
  score?: number;
  scoreLabel?: ScoreLabel;
};
