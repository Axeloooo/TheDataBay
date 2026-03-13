import type { MarketplaceDataItem } from "@/src/types/contract";

export type SimilaritySearchRequest = {
  query: string;
};

export type ScoreExplanation = {
  method: string;
  k_rows: number;
  rows_in_dataset: number;
  dimension: number;
  normalized: boolean;
};

export type RankedDataset = {
  item: MarketplaceDataItem;
  score: number;
  explanation: ScoreExplanation;
};

export type SimilaritySearchResponse = {
  query: string;
  results: RankedDataset[];
  count: number;
};
