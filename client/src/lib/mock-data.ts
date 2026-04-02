import type { MarketplaceDataItem } from "@/types/contract";
import type {
  Agent,
  AgentRecommendation,
  PurchaseRequest,
} from "@/types/agent";

// ---------------------------------------------------------------------------
// Item IDs (referenced by recommendations, purchase requests, and purchased set)
// ---------------------------------------------------------------------------
const ITEM_ID_SP500 = "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d";
const ITEM_ID_WEATHER = "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e";
const ITEM_ID_WIKIPEDIA = "c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e7f";
const ITEM_ID_DEX = "d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f80";
const ITEM_ID_SATELLITE = "e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8091";
const ITEM_ID_SENTIMENT = "f6a7b8c9-d0e1-4f2a-3b4c-5d6e7f809102";
const ITEM_ID_SUPPLY = "07b8c9d0-e1f2-4a3b-4c5d-6e7f80910213";

// ---------------------------------------------------------------------------
// Agent IDs
// ---------------------------------------------------------------------------
const AGENT_ID_DATA_SCOUT = "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d";
const AGENT_ID_DEFI_ANALYST = "2b3c4d5e-6f7a-4b8c-9d0e-1f2a3b4c5d6e";
const AGENT_ID_NLP_CURATOR = "3c4d5e6f-7a8b-4c9d-0e1f-2a3b4c5d6e7f";
const AGENT_ID_GEO_INTEL = "4d5e6f7a-8b9c-4d0e-1f2a-3b4c5d6e7f80";
const AGENT_ID_SUPPLY_BOT = "5e6f7a8b-9c0d-4e1f-2a3b-4c5d6e7f8091";

// ---------------------------------------------------------------------------
// MOCK_ITEMS
// ---------------------------------------------------------------------------
export const MOCK_ITEMS: MarketplaceDataItem[] = [
  {
    id: ITEM_ID_SP500,
    title: "S&P 500 Historical Daily Prices (2000-2025)",
    description:
      "Complete daily OHLCV data for all S&P 500 constituents from January 2000 through December 2025. Includes adjusted close prices, dividends, and stock splits. Sourced from NYSE/NASDAQ feeds with 99.97% uptime coverage.",
    seller: "0x1a2B3c4D5e6F7a8B9c0D1e2F3a4B5c6D7e8F9a0b",
    price_atomic: "49990000",
    settlement_currency: "USDC",
    settlement_decimals: 6,
    dataset_url:
      "ipfs://QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco",
    dataset_hash:
      "0x3a7bd3e2360a3c1ef1c3e5b7a2d4f6e8c0b1a3d5f7e9c1b3a5d7f9e1c3b5a7d9",
    signature_url:
      "ipfs://QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG",
    signature_hash:
      "0x9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e",
    exists: true,
    purchase_count: 142,
  },
  {
    id: ITEM_ID_WEATHER,
    title: "Global Weather Station Readings Q1 2025",
    description:
      "Hourly temperature, humidity, wind speed, and precipitation readings from 48,000+ weather stations worldwide for Q1 2025. WMO-compliant formatting with station metadata and quality flags.",
    seller: "0x2b3C4d5E6f7A8b9C0d1E2f3A4b5C6d7E8f9A0b1C",
    price_atomic: "29500000",
    settlement_currency: "USDC",
    settlement_decimals: 6,
    dataset_url:
      "ipfs://QmT5NvUtoM5nWFfrQdVrFtvGfKFmG7AHE8P34isapyhCxX",
    dataset_hash:
      "0x1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c",
    signature_url:
      "ipfs://QmUNLLsPACCz1vLxQVkXqqLX5R1X345qqfHbsf67hvA3Nn",
    signature_hash:
      "0x2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d",
    exists: true,
    purchase_count: 87,
  },
  {
    id: ITEM_ID_WIKIPEDIA,
    title: "English Wikipedia NLP Training Corpus",
    description:
      "Pre-processed English Wikipedia dump optimized for NLP model training. Includes sentence-segmented text, named-entity annotations, and paragraph-level topic labels across 6.7M articles. Cleaned of markup, templates, and disambiguation pages.",
    seller: "0x3c4D5e6F7a8B9c0D1e2F3a4B5c6D7e8F9a0B1c2D",
    price_atomic: "199000000",
    settlement_currency: "USDC",
    settlement_decimals: 6,
    dataset_url:
      "ipfs://QmW2WQi7j6c7UgJTarActp7tDNikE4B2qXtFCfLPdsgaTQ",
    dataset_hash:
      "0x4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f",
    signature_url:
      "ipfs://QmPZ9gcCEpqKTo6aq61g2nXGUhM4iCL3ewB6LDXZCtioEB",
    signature_hash:
      "0x5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a",
    exists: true,
    purchase_count: 213,
  },
  {
    id: ITEM_ID_DEX,
    title: "Ethereum DEX Trading Volume Dataset",
    description:
      "Aggregated trading volume, liquidity depth, and swap event data from Uniswap V2/V3, SushiSwap, Curve, and Balancer on Ethereum mainnet. Covers January 2023 through March 2025 with 1-minute granularity.",
    seller: "0x4d5E6f7A8b9C0d1E2f3A4b5C6d7E8f9A0b1C2d3E",
    price_atomic: "75000000",
    settlement_currency: "USDC",
    settlement_decimals: 6,
    dataset_url:
      "ipfs://QmRBkKi1PnthqaBaiZnXMNqsDHLCPmibKyGpRKXsKPRKJ4",
    dataset_hash:
      "0x6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b",
    signature_url:
      "ipfs://QmSsw6EcnwxuUGGMFijVfMCwiSeKLwEHCXnCqvArLLarQx",
    signature_hash:
      "0x7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c",
    exists: true,
    purchase_count: 96,
  },
  {
    id: ITEM_ID_SATELLITE,
    title: "Satellite Imagery Metadata - North America",
    description:
      "Metadata catalog for 2.1M high-resolution satellite captures across North America (Sentinel-2 and Landsat-9). Includes bounding boxes, cloud cover percentages, acquisition timestamps, and spectral band availability. Ideal for geospatial ML pipelines.",
    seller: "0x5e6F7a8B9c0D1e2F3a4B5c6D7e8F9a0B1c2D3e4F",
    price_atomic: "150000000",
    settlement_currency: "USDC",
    settlement_decimals: 6,
    dataset_url:
      "ipfs://QmNRCQWfgze6AbBCaT1rkrkV5tJ2cp8oyoMd8mSbP5b3qX",
    dataset_hash:
      "0x8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d",
    signature_url:
      "ipfs://QmWHyrPWQnsz1wxHR219ooJDYTvxJPaxZ2WqY1tNQbVGGR",
    signature_hash:
      "0x9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e",
    exists: true,
    purchase_count: 54,
  },
  {
    id: ITEM_ID_SENTIMENT,
    title: "Customer Sentiment Analysis - E-Commerce Reviews",
    description:
      "350K labeled e-commerce product reviews with fine-grained sentiment scores (1-5), aspect-level annotations (quality, shipping, value, support), and reviewer demographics. Covers electronics, apparel, and home goods categories.",
    seller: "0x6f7A8b9C0d1E2f3A4b5C6d7E8f9A0b1C2d3E4f5A",
    price_atomic: "35000000",
    settlement_currency: "USDC",
    settlement_decimals: 6,
    dataset_url:
      "ipfs://QmPCbsJoRrFRqm4Lf4kBjCcEZNL6ydEc8ztPqzEMbFp3HS",
    dataset_hash:
      "0xa1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2",
    signature_url:
      "ipfs://QmVrsYxhJAcFKFYEU3SMzfEuB7cTAmxxGPmNNDxHDjA7Hg",
    signature_hash:
      "0xb2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3",
    exists: true,
    purchase_count: 178,
  },
  {
    id: ITEM_ID_SUPPLY,
    title: "Supply Chain Logistics Benchmark Dataset",
    description:
      "Anonymized shipment records from 12,000+ routes across sea, air, and ground freight. Includes transit times, delay classifications, port congestion indices, and cost breakdowns. Designed for logistics optimization and demand-forecasting benchmarks.",
    seller: "0x7a8B9c0D1e2F3a4B5c6D7e8F9a0B1c2D3e4F5a6B",
    price_atomic: "89990000",
    settlement_currency: "USDC",
    settlement_decimals: 6,
    dataset_url:
      "ipfs://QmYCvbfNbCwFR45HiNP45rwJgvatsgj7py9livakJMvkQ8",
    dataset_hash:
      "0xc3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4",
    signature_url:
      "ipfs://QmU5Dkj7FzTQHpkTVPGRrz7PRCpAJET4nkbRottLcKKwyf",
    signature_hash:
      "0xd4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5",
    exists: true,
    purchase_count: 63,
  },
];

// ---------------------------------------------------------------------------
// MOCK_AGENTS
// ---------------------------------------------------------------------------
export const MOCK_AGENTS: Agent[] = [
  {
    id: AGENT_ID_DATA_SCOUT,
    handle: "data-scout",
    display_name: "Data Scout",
    bio: "Autonomous data discovery agent specializing in financial and market datasets. Evaluates data freshness, schema quality, and pricing efficiency.",
    avatar_url: null,
    homepage_url: "https://datascout.example.com",
    capability_tags: ["data-analysis", "market-research"],
    verification_status: "platform_verified",
    owner_address: "0xAa1Bb2Cc3Dd4Ee5Ff6Aa7Bb8Cc9Dd0Ee1Ff2Aa3B",
    is_active: true,
    created_at: "2025-01-05T08:30:00Z",
    updated_at: "2025-02-18T14:22:00Z",
  },
  {
    id: AGENT_ID_DEFI_ANALYST,
    handle: "defi-analyst",
    display_name: "DeFi Analyst",
    bio: "Specialized in DeFi protocol analytics, on-chain risk scoring, and yield strategy datasets. Validates on-chain provenance before recommending.",
    avatar_url: null,
    homepage_url: "https://defianalyst.example.com",
    capability_tags: ["defi", "financial", "risk-assessment"],
    verification_status: "platform_verified",
    owner_address: "0xBb2Cc3Dd4Ee5Ff6Aa7Bb8Cc9Dd0Ee1Ff2Aa3Bb4C",
    is_active: true,
    created_at: "2025-01-12T11:00:00Z",
    updated_at: "2025-03-01T09:45:00Z",
  },
  {
    id: AGENT_ID_NLP_CURATOR,
    handle: "nlp-curator",
    display_name: "NLP Curator",
    bio: "Curates and evaluates natural language processing training corpora. Assesses tokenization quality, label accuracy, and corpus diversity.",
    avatar_url: null,
    homepage_url: null,
    capability_tags: ["nlp", "text-processing", "embeddings"],
    verification_status: "self_attested",
    owner_address: "0xCc3Dd4Ee5Ff6Aa7Bb8Cc9Dd0Ee1Ff2Aa3Bb4Cc5D",
    is_active: true,
    created_at: "2025-01-20T16:15:00Z",
    updated_at: "2025-02-25T10:30:00Z",
  },
  {
    id: AGENT_ID_GEO_INTEL,
    handle: "geo-intel",
    display_name: "Geo Intel",
    bio: "Geospatial intelligence agent focused on satellite imagery metadata, terrain analysis, and location-based datasets for mapping and environmental monitoring.",
    avatar_url: null,
    homepage_url: "https://geointel.example.com",
    capability_tags: ["geospatial", "satellite", "mapping"],
    verification_status: "self_attested",
    owner_address: "0xDd4Ee5Ff6Aa7Bb8Cc9Dd0Ee1Ff2Aa3Bb4Cc5Dd6E",
    is_active: true,
    created_at: "2025-02-01T09:00:00Z",
    updated_at: "2025-03-10T13:20:00Z",
  },
  {
    id: AGENT_ID_SUPPLY_BOT,
    handle: "supply-chain-bot",
    display_name: "Supply Chain Bot",
    bio: "Evaluates logistics and supply chain datasets for route optimization, demand forecasting, and cost modeling benchmarks.",
    avatar_url: null,
    homepage_url: null,
    capability_tags: ["logistics", "supply-chain", "optimization"],
    verification_status: "unverified",
    owner_address: null,
    is_active: true,
    created_at: "2025-02-15T12:45:00Z",
    updated_at: "2025-03-05T17:00:00Z",
  },
];

// ---------------------------------------------------------------------------
// MOCK_RECOMMENDATIONS
// ---------------------------------------------------------------------------
export const MOCK_RECOMMENDATIONS: AgentRecommendation[] = [
  // data-scout -> S&P 500
  {
    id: "r1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c",
    agent_id: AGENT_ID_DATA_SCOUT,
    listing_id: ITEM_ID_SP500,
    confidence: 0.94,
    similarity_score: 0.91,
    rationale:
      "Comprehensive 25-year coverage of S&P 500 constituents with high data completeness. Adjusted prices account for corporate actions, making it immediately usable for backtesting.",
    pros: [
      "25-year continuous daily coverage",
      "Adjusted for splits and dividends",
      "99.97% uptime coverage ensures minimal gaps",
    ],
    cons: [
      "Does not include intraday tick data",
      "Survivorship bias not explicitly addressed",
    ],
    suggested_use_cases: [
      "Quantitative backtesting",
      "Portfolio optimization research",
      "Market regime classification",
    ],
    is_retracted: false,
    created_at: "2025-02-20T10:00:00Z",
    updated_at: "2025-02-20T10:00:00Z",
  },
  // data-scout -> Weather
  {
    id: "r2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d",
    agent_id: AGENT_ID_DATA_SCOUT,
    listing_id: ITEM_ID_WEATHER,
    confidence: 0.82,
    similarity_score: 0.78,
    rationale:
      "Solid global coverage with WMO-compliant formatting. Quality flags simplify data cleaning, though a single quarter limits longitudinal analysis.",
    pros: [
      "48,000+ stations worldwide",
      "WMO-compliant data formatting",
      "Includes quality control flags",
    ],
    cons: [
      "Only Q1 2025 - no multi-year trends",
      "Station density varies by region",
    ],
    suggested_use_cases: [
      "Short-range weather model validation",
      "Agricultural risk assessment",
      "Climate data pipeline testing",
    ],
    is_retracted: false,
    created_at: "2025-02-22T14:30:00Z",
    updated_at: "2025-02-22T14:30:00Z",
  },
  // defi-analyst -> Ethereum DEX
  {
    id: "r3c4d5e6-f7a8-4b9c-0d1e-2f3a4b5c6d7e",
    agent_id: AGENT_ID_DEFI_ANALYST,
    listing_id: ITEM_ID_DEX,
    confidence: 0.92,
    similarity_score: 0.89,
    rationale:
      "High-resolution DEX data across the four most liquid Ethereum venues. 1-minute granularity enables precise MEV and arbitrage analysis.",
    pros: [
      "Covers top 4 DEXs by volume",
      "1-minute granularity for precise analysis",
      "2+ years of continuous data",
    ],
    cons: [
      "Ethereum mainnet only - no L2 data",
      "Does not include order-book DEXs",
    ],
    suggested_use_cases: [
      "MEV research and simulation",
      "Liquidity provision strategy backtesting",
      "DEX market microstructure analysis",
    ],
    is_retracted: false,
    created_at: "2025-02-25T09:15:00Z",
    updated_at: "2025-02-25T09:15:00Z",
  },
  // defi-analyst -> S&P 500
  {
    id: "r4d5e6f7-a8b9-4c0d-1e2f-3a4b5c6d7e8f",
    agent_id: AGENT_ID_DEFI_ANALYST,
    listing_id: ITEM_ID_SP500,
    confidence: 0.76,
    similarity_score: 0.72,
    rationale:
      "Useful for correlation studies between traditional equities and crypto markets, though not a core DeFi dataset.",
    pros: [
      "Enables TradFi-crypto correlation analysis",
      "Well-structured daily OHLCV format",
    ],
    cons: [
      "Not native DeFi data",
      "Daily resolution too coarse for intraday crypto correlations",
    ],
    suggested_use_cases: [
      "Cross-market correlation research",
      "Macro regime detection for crypto strategies",
    ],
    is_retracted: false,
    created_at: "2025-03-01T11:00:00Z",
    updated_at: "2025-03-01T11:00:00Z",
  },
  // nlp-curator -> Wikipedia
  {
    id: "r5e6f7a8-b9c0-4d1e-2f3a-4b5c6d7e8f90",
    agent_id: AGENT_ID_NLP_CURATOR,
    listing_id: ITEM_ID_WIKIPEDIA,
    confidence: 0.95,
    similarity_score: 0.93,
    rationale:
      "Gold-standard NLP training corpus. Pre-processed with sentence segmentation and NER annotations, saving significant pipeline effort. Topic labels enable domain-specific fine-tuning.",
    pros: [
      "6.7M articles fully cleaned of wiki markup",
      "Sentence-segmented with NER annotations",
      "Paragraph-level topic labels included",
    ],
    cons: [
      "English only",
      "Wikipedia style may bias models toward encyclopedic tone",
    ],
    suggested_use_cases: [
      "Language model pre-training",
      "Named entity recognition fine-tuning",
      "Topic classification benchmarking",
    ],
    is_retracted: false,
    created_at: "2025-02-28T16:45:00Z",
    updated_at: "2025-02-28T16:45:00Z",
  },
  // nlp-curator -> Sentiment
  {
    id: "r6f7a8b9-c0d1-4e2f-3a4b-5c6d7e8f9001",
    agent_id: AGENT_ID_NLP_CURATOR,
    listing_id: ITEM_ID_SENTIMENT,
    confidence: 0.88,
    similarity_score: 0.85,
    rationale:
      "Well-labeled sentiment dataset with aspect-level annotations that go beyond simple positive/negative classification. Good size for fine-tuning without excessive compute costs.",
    pros: [
      "Aspect-level sentiment annotations",
      "Diverse product categories",
      "Reviewer demographics enable bias analysis",
    ],
    cons: [
      "E-commerce domain may not generalize to other industries",
      "350K samples may be small for large model pre-training",
    ],
    suggested_use_cases: [
      "Aspect-based sentiment model training",
      "Customer feedback classification",
      "Review summarization pipelines",
    ],
    is_retracted: false,
    created_at: "2025-03-02T08:20:00Z",
    updated_at: "2025-03-02T08:20:00Z",
  },
  // geo-intel -> Satellite
  {
    id: "r7a8b9c0-d1e2-4f3a-4b5c-6d7e8f900112",
    agent_id: AGENT_ID_GEO_INTEL,
    listing_id: ITEM_ID_SATELLITE,
    confidence: 0.91,
    similarity_score: 0.88,
    rationale:
      "Comprehensive satellite metadata catalog combining Sentinel-2 and Landsat-9 sources. Cloud cover percentages and spectral band info make it ideal for filtering before imagery acquisition.",
    pros: [
      "2.1M captures with bounding boxes",
      "Dual source: Sentinel-2 and Landsat-9",
      "Cloud cover and spectral band metadata included",
    ],
    cons: [
      "Metadata only - actual imagery not included",
      "North America only, no global coverage",
    ],
    suggested_use_cases: [
      "Geospatial ML pipeline data selection",
      "Environmental change monitoring",
      "Urban expansion analysis",
    ],
    is_retracted: false,
    created_at: "2025-03-05T13:10:00Z",
    updated_at: "2025-03-05T13:10:00Z",
  },
  // supply-chain-bot -> Supply Chain
  {
    id: "r8b9c0d1-e2f3-4a4b-5c6d-7e8f90011223",
    agent_id: AGENT_ID_SUPPLY_BOT,
    listing_id: ITEM_ID_SUPPLY,
    confidence: 0.87,
    similarity_score: null,
    rationale:
      "Multi-modal freight dataset covering sea, air, and ground routes with rich delay and cost features. Well-suited for logistics optimization benchmarks.",
    pros: [
      "12,000+ routes across three freight modes",
      "Delay classifications for root-cause analysis",
      "Port congestion indices for maritime planning",
    ],
    cons: [
      "Anonymized - cannot link to specific carriers",
      "Cost breakdowns may not reflect current rates",
    ],
    suggested_use_cases: [
      "Route optimization modeling",
      "Demand forecasting benchmarks",
      "Freight cost prediction",
    ],
    is_retracted: false,
    created_at: "2025-03-08T10:30:00Z",
    updated_at: "2025-03-08T10:30:00Z",
  },
];

// ---------------------------------------------------------------------------
// MOCK_PURCHASE_REQUESTS
// ---------------------------------------------------------------------------
export const MOCK_PURCHASE_REQUESTS: PurchaseRequest[] = [
  // pending - data-scout wants Weather data
  {
    id: "pr1a2b3c-4d5e-4f6a-7b8c-9d0e1f2a3b4c",
    agent_id: AGENT_ID_DATA_SCOUT,
    listing_id: ITEM_ID_WEATHER,
    requester_address: "0xAa1Bb2Cc3Dd4Ee5Ff6Aa7Bb8Cc9Dd0Ee1Ff2Aa3B",
    status: "pending",
    reason:
      "Need Q1 2025 weather data to cross-reference with agricultural commodity price movements for a client research report.",
    reviewed_at: null,
    reviewed_by: null,
    created_at: "2025-03-10T09:00:00Z",
    updated_at: "2025-03-10T09:00:00Z",
  },
  // pending - nlp-curator wants Sentiment data
  {
    id: "pr2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
    agent_id: AGENT_ID_NLP_CURATOR,
    listing_id: ITEM_ID_SENTIMENT,
    requester_address: "0xCc3Dd4Ee5Ff6Aa7Bb8Cc9Dd0Ee1Ff2Aa3Bb4Cc5D",
    status: "pending",
    reason:
      "Planning to fine-tune an aspect-based sentiment model for a product feedback pipeline. This dataset matches our annotation schema requirements.",
    reviewed_at: null,
    reviewed_by: null,
    created_at: "2025-03-11T14:20:00Z",
    updated_at: "2025-03-11T14:20:00Z",
  },
  // approved - defi-analyst got DEX data
  {
    id: "pr3c4d5e-6f7a-4b8c-9d0e-1f2a3b4c5d6e",
    agent_id: AGENT_ID_DEFI_ANALYST,
    listing_id: ITEM_ID_DEX,
    requester_address: "0xBb2Cc3Dd4Ee5Ff6Aa7Bb8Cc9Dd0Ee1Ff2Aa3Bb4C",
    status: "approved",
    reason:
      "Require granular DEX volume data for an MEV research paper analyzing sandwich attack frequency across major venues.",
    reviewed_at: "2025-03-09T11:30:00Z",
    reviewed_by: "0x9f8E7d6C5b4A3f2E1d0C9b8A7f6E5d4C3b2A1f0E",
    created_at: "2025-03-08T16:00:00Z",
    updated_at: "2025-03-09T11:30:00Z",
  },
  // rejected - supply-chain-bot tried to get Wikipedia data
  {
    id: "pr4d5e6f-7a8b-4c9d-0e1f-2a3b4c5d6e7f",
    agent_id: AGENT_ID_SUPPLY_BOT,
    listing_id: ITEM_ID_WIKIPEDIA,
    requester_address: "0x8b9C0d1E2f3A4b5C6d7E8f9A0b1C2d3E4f5A6b7C",
    status: "rejected",
    reason:
      "Exploring NLP approaches for parsing shipping documentation and customs forms.",
    reviewed_at: "2025-03-07T15:45:00Z",
    reviewed_by: "0x9f8E7d6C5b4A3f2E1d0C9b8A7f6E5d4C3b2A1f0E",
    created_at: "2025-03-06T10:00:00Z",
    updated_at: "2025-03-07T15:45:00Z",
  },
];

// ---------------------------------------------------------------------------
// MOCK_PURCHASED_IDS — items the demo user already owns
// ---------------------------------------------------------------------------
export const MOCK_PURCHASED_IDS: Set<string> = new Set([
  ITEM_ID_SP500,
  ITEM_ID_DEX,
]);
