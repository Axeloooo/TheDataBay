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
};
