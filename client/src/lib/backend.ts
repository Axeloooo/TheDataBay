import { apiRequest } from "@/lib/api";
import type {
  MarketplaceDataItem,
  AccessCheckResponse,
  WalletAccessRequest,
  PurchasedItemsRequest,
  PurchasedItemsResponse,
} from "@/types/contract";
import type { KeyReleaseRequest, KeyReleaseResponse } from "@/types/dataset";
import type { JobResponse, JobStatusResponse } from "@/types/llm";
import type { SimilaritySearchRequest, SimilaritySearchResponse } from "@/types/ai";
import type { Agent, AgentListResponse, RecommendationListResponse, PurchaseRequest, PurchaseRequestListResponse } from "@/types/agent";

type MarketplaceApiItem = Omit<
  MarketplaceDataItem,
  "price_atomic" | "settlement_currency" | "settlement_decimals"
> & {
  price?: unknown;
  price_atomic?: unknown;
  settlement_currency?: unknown;
  settlement_decimals?: unknown;
};

function normalizeAtomicString(value: unknown): string {
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!/^\d+$/.test(trimmed)) {
      throw new Error("Invalid marketplace price format from API.");
    }
    return trimmed;
  }

  if (typeof value === "number") {
    if (!Number.isFinite(value) || !Number.isInteger(value) || value < 0) {
      throw new Error("Invalid marketplace price number from API.");
    }
    if (!Number.isSafeInteger(value)) {
      throw new Error(
        "Marketplace price exceeds safe integer precision. API must return atomic units as a string.",
      );
    }
    return value.toString();
  }

  throw new Error("Unsupported marketplace price type from API.");
}

function normalizeMarketplaceItem(item: MarketplaceApiItem): MarketplaceDataItem {
  const priceAtomic = item.price_atomic ?? item.price;
  if (priceAtomic === undefined || priceAtomic === null) {
    throw new Error("Missing marketplace price from API.");
  }

  const rawSettlementCurrency = item.settlement_currency;
  const settlementCurrency = rawSettlementCurrency == null
    ? "USDC"
    : String(rawSettlementCurrency).trim().toUpperCase();
  if (settlementCurrency !== "USDC") {
    throw new Error("Unsupported marketplace settlement currency from API.");
  }
  if (
    rawSettlementCurrency != null &&
    String(rawSettlementCurrency) !== "USDC" &&
    settlementCurrency === "USDC"
  ) {
    // Soft warning: backend returned USDC in a non-canonical format (e.g., wrong case/whitespace).
    // This keeps the UI resilient while still surfacing potential backend drift.
    console.warn(
      "Non-canonical marketplace settlement currency from API; normalized to USDC:",
      rawSettlementCurrency,
    );
  }

  const settlementDecimals = Number(item.settlement_decimals ?? 6);
  if (settlementDecimals !== 6) {
    throw new Error("Unsupported marketplace settlement decimals from API.");
  }

  const rest = { ...item };
  delete rest.price;
  delete rest.price_atomic;
  delete rest.settlement_currency;
  delete rest.settlement_decimals;

  return {
    ...rest,
    price_atomic: normalizeAtomicString(priceAtomic),
    settlement_currency: "USDC",
    settlement_decimals: 6,
  };
}

export const backend = {
  submitEmbedBatch: (formData: FormData) =>
    apiRequest<JobResponse>("/api/v1/llm/embed/batch", {
      method: "POST",
      body: formData,
    }),

  getJobStatus: (jobId: string) =>
    apiRequest<JobStatusResponse>(`/api/v1/llm/jobs/${jobId}`),

  getMarketplaceItems: async () => {
    const items = await apiRequest<MarketplaceApiItem[]>("/api/v1/contract/items/all");
    return items.map(normalizeMarketplaceItem);
  },

  getMarketplaceItem: async (listingId: string) => {
    const item = await apiRequest<MarketplaceApiItem>(`/api/v1/contract/items/${listingId}`);
    return normalizeMarketplaceItem(item);
  },

  requestKeyRelease: (listingId: string, payload: KeyReleaseRequest) =>
    apiRequest<KeyReleaseResponse>(`/api/v1/datasets/${listingId}/key`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  checkAccess: (listingId: string, payload: WalletAccessRequest) =>
    apiRequest<AccessCheckResponse>(`/api/v1/contract/access/${listingId}/check`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  similaritySearch: async (payload: SimilaritySearchRequest) => {
    const response = await apiRequest<SimilaritySearchResponse>("/api/v1/ai/similarity-search", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    return {
      ...response,
      results: response.results.map((result) => ({
        ...result,
        item: normalizeMarketplaceItem(result.item as MarketplaceApiItem),
      })),
    };
  },

  getPurchasedItemsByWallet: async (payload: PurchasedItemsRequest) => {
    const response = await apiRequest<PurchasedItemsResponse>("/api/v1/contract/purchases/by-wallet", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    return {
      ...response,
      items: response.items.map((item) =>
        normalizeMarketplaceItem(item as MarketplaceApiItem),
      ),
    };
  },

  // Agent endpoints
  getAgents: (params?: { search?: string; tag?: string; status?: string; offset?: number; limit?: number }) => {
    const searchParams = new URLSearchParams();
    if (params?.search) searchParams.set("search", params.search);
    if (params?.tag) searchParams.set("tag", params.tag);
    if (params?.status) searchParams.set("status", params.status);
    if (params?.offset !== undefined) searchParams.set("offset", String(params.offset));
    if (params?.limit !== undefined) searchParams.set("limit", String(params.limit));
    const qs = searchParams.toString();
    return apiRequest<AgentListResponse>(`/api/v1/agents${qs ? "?" + qs : ""}`);
  },

  getAgent: (handle: string) =>
    apiRequest<Agent>(`/api/v1/agents/${handle}`),

  getAgentRecommendations: (handle: string, params?: { offset?: number; limit?: number }) => {
    const searchParams = new URLSearchParams();
    if (params?.offset !== undefined) searchParams.set("offset", String(params.offset));
    if (params?.limit !== undefined) searchParams.set("limit", String(params.limit));
    const qs = searchParams.toString();
    return apiRequest<RecommendationListResponse>(`/api/v1/agents/${handle}/recommendations${qs ? "?" + qs : ""}`);
  },

  getRecommendationsForListing: (listingId: string) =>
    apiRequest<RecommendationListResponse>(`/api/v1/recommendations/by-listing/${listingId}`),

  getPurchaseRequests: (params?: { status?: string; offset?: number; limit?: number }) => {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set("status", params.status);
    if (params?.offset !== undefined) searchParams.set("offset", String(params.offset));
    if (params?.limit !== undefined) searchParams.set("limit", String(params.limit));
    const qs = searchParams.toString();
    return apiRequest<PurchaseRequestListResponse>(`/api/v1/purchase-requests${qs ? "?" + qs : ""}`);
  },

  reviewPurchaseRequest: (requestId: string, payload: { status: "approved" | "rejected"; reviewed_by: string }) =>
    apiRequest<PurchaseRequest>(`/api/v1/purchase-requests/${requestId}/review`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
