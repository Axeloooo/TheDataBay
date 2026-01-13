export type VectorSpec = {
  embeddingModel: string;
  dimension: number;
  distanceMetric: "cosine" | "l2";
  normalized: boolean;
  templateVersion: string;
};

export type DatasetRecord = {
  id: string;

  // Core listing
  title: string;
  description: string;
  priceEth: number;

  // IPFS
  accessUri: string;
  vectorUri: string;
  metadataUri: string;

  // Integrity
  accessSha256: string;
  vectorSha256: string;
  vectorSpec: VectorSpec;

  // Dataset stats
  rows: number;
  columns: number;
  fileSizeMB: number;
  format: "csv" | "parquet";
  domain: string;
  tags: string[];

  // ML-specific
  target?: {
    name: string;
    type: "binary" | "multiclass" | "regression";
  };

  // Seller
  seller: string;
  createdAt: string;

  // UI / marketplace
  verified: boolean;
  downloads: number;
};
