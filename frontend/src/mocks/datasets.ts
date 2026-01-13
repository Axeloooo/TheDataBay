import type { DatasetRecord } from "@/types/dataset";

export const MOCK_DATASETS: DatasetRecord[] = [
  {
    id: "uci-heart-disease-v1",
    title: "UCI Heart Disease Dataset (Embedding-Ready)",
    description:
      "Clinical and demographic features for heart disease prediction. Includes per-record embeddings for semantic retrieval.",
    priceEth: 0.05,

    accessUri: "ipfs://bafyheartdatasetcsv",
    vectorUri: "ipfs://bafyheartvectorsjson",
    metadataUri: "ipfs://bafyheartmetadata",

    accessSha256: "0xaaa111...",
    vectorSha256: "0xbbb222...",

    vectorSpec: {
      embeddingModel: "text-embedding-3-large",
      dimension: 1536,
      distanceMetric: "cosine",
      normalized: true,
      templateVersion: "v1",
    },

    rows: 303,
    columns: 14,
    fileSizeMB: 0.4,
    format: "csv",
    domain: "Healthcare",
    tags: ["healthcare", "classification", "embeddings", "ml"],

    target: {
      name: "presence_of_heart_disease",
      type: "binary",
    },

    seller: "0xA1b2c3D4e5F678901234567890ABCDEF12345678",
    createdAt: "2025-01-01T12:00:00Z",

    verified: true,
    downloads: 128,
  },

  {
    id: "synthetic-clinical-labs-v2",
    title: "Synthetic Clinical Lab Results Dataset",
    description:
      "Large synthetic dataset of lab measurements designed for retrieval-augmented clinical ML experiments.",
    priceEth: 0.12,

    accessUri: "ipfs://bafysyntheticcsv",
    vectorUri: "ipfs://bafysyntheticvectors",
    metadataUri: "ipfs://bafysyntheticmetadata",

    accessSha256: "0xccc333...",
    vectorSha256: "0xddd444...",

    vectorSpec: {
      embeddingModel: "bge-large-en",
      dimension: 1024,
      distanceMetric: "cosine",
      normalized: true,
      templateVersion: "v2",
    },

    rows: 25000,
    columns: 22,
    fileSizeMB: 12.8,
    format: "csv",
    domain: "Healthcare",
    tags: ["synthetic", "retrieval", "embeddings"],

    target: {
      name: "risk_score",
      type: "regression",
    },

    seller: "0x99887766554433221100aabbccddeeff00112233",
    createdAt: "2024-12-10T09:30:00Z",

    verified: false,
    downloads: 42,
  },

  {
    id: "financial-transactions-embeddings",
    title: "Anonymized Financial Transactions (Vectorized)",
    description:
      "Transaction-level financial data with embeddings optimized for anomaly detection and semantic search.",
    priceEth: 0.2,

    accessUri: "ipfs://bafyfinancialcsv",
    vectorUri: "ipfs://bafyfinancialvectors",
    metadataUri: "ipfs://bafyfinancialmetadata",

    accessSha256: "0xeee555...",
    vectorSha256: "0xfff666...",

    vectorSpec: {
      embeddingModel: "text-embedding-3-small",
      dimension: 768,
      distanceMetric: "cosine",
      normalized: true,
      templateVersion: "v1",
    },

    rows: 100000,
    columns: 18,
    fileSizeMB: 48.2,
    format: "csv",
    domain: "Finance",
    tags: ["finance", "anomaly-detection", "embeddings"],

    seller: "0x123400000000000000000000000000000000abcd",
    createdAt: "2024-11-22T16:45:00Z",

    verified: true,
    downloads: 301,
  },
];
