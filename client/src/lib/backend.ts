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
import type {
  SimilaritySearchRequest,
  SimilaritySearchResponse,
  CardViewModel,
} from "@/types/ai";
import type {
  Agent,
  AgentListResponse,
  RecommendationListResponse,
  PurchaseRequest,
  PurchaseRequestListResponse,
} from "@/types/agent";
import { normalizeAtomicString } from "@/lib/atomic";
import { uuidToBytes32 } from "@/lib/ids";

type MarketplaceApiItem = Omit<
  MarketplaceDataItem,
  "payment_token" | "price_atomic" | "settlement_currency" | "settlement_decimals"
> & {
  payment_token?: unknown;
  paymentToken?: unknown;
  price?: unknown;
  price_atomic?: unknown;
  settlement_currency?: unknown;
  settlement_decimals?: unknown;
};

function normalizeMarketplaceItem(
  item: MarketplaceApiItem,
): MarketplaceDataItem {
  const priceAtomic = item.price_atomic ?? item.price;
  if (priceAtomic === undefined || priceAtomic === null) {
    throw new Error("Missing marketplace price from API.");
  }
  const rawPaymentToken = item.payment_token ?? item.paymentToken;
  if (typeof rawPaymentToken !== "string" || !rawPaymentToken.trim()) {
    throw new Error("Missing marketplace payment token from API.");
  }

  const rawSettlementCurrency = item.settlement_currency;
  const settlementCurrency =
    rawSettlementCurrency == null
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
  delete rest.paymentToken;
  delete rest.payment_token;
  delete rest.price_atomic;
  delete rest.settlement_currency;
  delete rest.settlement_decimals;

  return {
    ...rest,
    payment_token: rawPaymentToken.trim(),
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
    const items = await apiRequest<MarketplaceApiItem[]>(
      "/api/v1/contract/items/all",
    );
    return items.map(normalizeMarketplaceItem);
  },

  getMarketplaceItem: async (listingId: string) => {
    const item = await apiRequest<MarketplaceApiItem>(
      `/api/v1/contract/items/${listingId}`,
    );
    return normalizeMarketplaceItem(item);
  },

  requestKeyRelease: (listingId: string, payload: KeyReleaseRequest) =>
    apiRequest<KeyReleaseResponse>(`/api/v1/datasets/${listingId}/key`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  checkAccess: (listingId: string, payload: WalletAccessRequest) =>
    apiRequest<AccessCheckResponse>(
      `/api/v1/contract/access/${listingId}/check`,
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
    ),

  similaritySearch: async (
    payload: SimilaritySearchRequest,
  ): Promise<{ query: string; results: CardViewModel[]; count: number }> => {
    const response = await apiRequest<SimilaritySearchResponse>(
      "/api/v1/ai/similarity-search",
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
    );
    return {
      query: response.query,
      count: response.count,
      results: response.results.map((r) => ({
        dataset: {
          id: uuidToBytes32(r.listing_id),
          title: r.title,
          description: r.description,
          payment_token: r.payment_token,
          price_atomic: String(r.price_atomic),
          settlement_currency: r.settlement_currency,
          settlement_decimals: r.settlement_decimals,
          purchase_count: r.purchase_count,
        },
        score: r.score,
        scoreLabel: r.score_label,
      })),
    };
  },

  getPurchasedItemsByWallet: async (payload: PurchasedItemsRequest) => {
    const response = await apiRequest<PurchasedItemsResponse>(
      "/api/v1/contract/purchases/by-wallet",
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
    );
    return {
      ...response,
      items: response.items.map((item) =>
        normalizeMarketplaceItem(item as MarketplaceApiItem),
      ),
    };
  },

  // Agent endpoints
  getAgents: (params?: {
    search?: string;
    tag?: string;
    status?: string;
    offset?: number;
    limit?: number;
  }) => {
    const searchParams = new URLSearchParams();
    if (params?.search) searchParams.set("search", params.search);
    if (params?.tag) searchParams.set("tag", params.tag);
    if (params?.status) searchParams.set("status", params.status);
    if (params?.offset !== undefined)
      searchParams.set("offset", String(params.offset));
    if (params?.limit !== undefined)
      searchParams.set("limit", String(params.limit));
    const qs = searchParams.toString();
    return apiRequest<AgentListResponse>(`/api/v1/agents${qs ? "?" + qs : ""}`);
  },

  getAgent: (handle: string) => apiRequest<Agent>(`/api/v1/agents/${handle}`),

  getAgentRecommendations: (
    handle: string,
    params?: { offset?: number; limit?: number },
  ) => {
    const searchParams = new URLSearchParams();
    if (params?.offset !== undefined)
      searchParams.set("offset", String(params.offset));
    if (params?.limit !== undefined)
      searchParams.set("limit", String(params.limit));
    const qs = searchParams.toString();
    return apiRequest<RecommendationListResponse>(
      `/api/v1/agents/${handle}/recommendations${qs ? "?" + qs : ""}`,
    );
  },

  getRecommendationsForListing: (listingId: string) =>
    apiRequest<RecommendationListResponse>(
      `/api/v1/recommendations/by-listing/${listingId}`,
    ),

  getPurchaseRequests: (params?: {
    status?: string;
    offset?: number;
    limit?: number;
  }) => {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set("status", params.status);
    if (params?.offset !== undefined)
      searchParams.set("offset", String(params.offset));
    if (params?.limit !== undefined)
      searchParams.set("limit", String(params.limit));
    const qs = searchParams.toString();
    return apiRequest<PurchaseRequestListResponse>(
      `/api/v1/purchase-requests${qs ? "?" + qs : ""}`,
    );
  },

  reviewPurchaseRequest: (
    requestId: string,
    payload: { status: "approved" | "rejected"; reviewed_by: string },
  ) =>
    apiRequest<PurchaseRequest>(
      `/api/v1/purchase-requests/${requestId}/review`,
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
    ),
};
