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
        "Marketplace price exceeds safe integer precision. API must return atomic units as a string.",
      );
    }

    return value.toString();
  }

  throw new Error("Unsupported marketplace price type from API.");
}

function normalizeMarketplaceItem(
  item: MarketplaceApiItem,
): MarketplaceDataItem {
  const priceAtomic = item.price_atomic ?? item.price;
  if (priceAtomic === undefined || priceAtomic === null) {
    throw new Error("Missing marketplace price from API.");
  }

  const settlementCurrency = String(item.settlement_currency ?? "USDC");
  if (settlementCurrency !== "USDC") {
    throw new Error("Unsupported marketplace settlement currency from API.");
  }

  const settlementDecimals = Number(item.settlement_decimals ?? 6);
  if (settlementDecimals !== 6) {
    throw new Error("Unsupported marketplace settlement decimals from API.");
  }

  const {
    price: _legacyPrice,
    price_atomic: _legacyAtomic,
    settlement_currency: _legacyCurrency,
    settlement_decimals: _legacyDecimals,
    ...rest
  } = item;

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
