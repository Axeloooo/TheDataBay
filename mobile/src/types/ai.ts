import type { MarketplaceDataItem } from "@/src/types/contract";

export type SimilaritySearchRequest = {
  query: string;
};

export type ScoreLabel = "high" | "moderate" | "low";

export type RankedDataset = {
  item: MarketplaceDataItem;
  score: number;
  score_label: ScoreLabel;
};

export type SimilaritySearchResponse = {
  query: string;
  results: RankedDataset[];
  count: number;
};

export type RawRankedDataset = {
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

export type RawSimilaritySearchResponse = {
  query: string;
  results: RawRankedDataset[];
  count: number;
};
