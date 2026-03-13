import { apiRequest } from "@/src/lib/api";
import type {
  MarketplaceDataItem,
  AccessCheckResponse,
  WalletAccessRequest,
  PurchasedItemsRequest,
  PurchasedItemsResponse,
} from "@/src/types/contract";
import type {
  KeyReleaseRequest,
  KeyReleaseResponse,
} from "@/src/types/dataset";
import type { JobResponse, JobStatusResponse } from "@/src/types/llm";
import type {
  SimilaritySearchRequest,
  SimilaritySearchResponse,
} from "@/src/types/ai";

function normalizeWeiString(value: unknown): string {
  if (typeof value === "string") {
    if (!/^\d+$/.test(value)) {
      throw new Error("Invalid marketplace price format from API.");
    }
    return value;
  }

  if (typeof value === "number") {
    if (!Number.isFinite(value) || !Number.isInteger(value) || value < 0) {
      throw new Error("Invalid marketplace price number from API.");
    }

    if (!Number.isSafeInteger(value)) {
      throw new Error(
        "Marketplace price exceeds safe integer precision. API must return wei as a string.",
      );
    }

    return value.toString();
  }

  throw new Error("Unsupported marketplace price type from API.");
}

function normalizeMarketplaceItem(
  item: MarketplaceDataItem,
): MarketplaceDataItem {
  return {
    ...item,
    price: normalizeWeiString(item.price),
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
    const items = await apiRequest<MarketplaceDataItem[]>(
      "/api/v1/contract/items/all",
    );
    return items.map(normalizeMarketplaceItem);
  },

  getMarketplaceItem: async (listingId: string) => {
    const item = await apiRequest<MarketplaceDataItem>(
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

  similaritySearch: (payload: SimilaritySearchRequest) =>
    apiRequest<SimilaritySearchResponse>("/api/v1/ai/similarity-search", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

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
      items: response.items.map(normalizeMarketplaceItem),
    };
  },
};
