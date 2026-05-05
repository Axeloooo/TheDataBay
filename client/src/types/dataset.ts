export type WalletType = "evm" | "solana" | string;

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

export type VectorSpec = {
  model: string;
  dimension: number;
};

export type DatasetStats = {
  total_rows: number;
  total_columns: number;
  has_header: boolean;
  empty_rows_skipped: number;
};

export type DatasetPreview = {
  column_names: string[];
  rows: string[][];
};

export type DatasetEmbedResponse = {
  listing_id: string;
  dataset_url: string;
  dataset_hash: string;
  preview: DatasetPreview;
  stats: DatasetStats;
  vector_spec: VectorSpec;
};
