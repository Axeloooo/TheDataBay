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

export const backend = {
  submitEmbedBatch: (formData: FormData) =>
    apiRequest<JobResponse>("/api/v1/llm/embed/batch", {
      method: "POST",
      body: formData,
    }),

  getJobStatus: (jobId: string) =>
    apiRequest<JobStatusResponse>(`/api/v1/llm/jobs/${jobId}`),

  getMarketplaceItems: () =>
    apiRequest<MarketplaceDataItem[]>("/api/v1/contract/items/all"),

  getMarketplaceItem: (listingId: string) =>
    apiRequest<MarketplaceDataItem>(`/api/v1/contract/items/${listingId}`),

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

  similaritySearch: (payload: SimilaritySearchRequest) =>
    apiRequest<SimilaritySearchResponse>("/api/v1/ai/similarity-search", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getPurchasedItemsByWallet: (payload: PurchasedItemsRequest) =>
    apiRequest<PurchasedItemsResponse>("/api/v1/contract/purchases/by-wallet", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

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
