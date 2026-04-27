import { apiRequest } from "@/src/lib/api";
import type {
  MarketplaceDataItem,
  MarketplaceSettlementCurrency,
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
  RawSimilaritySearchResponse,
  SimilaritySearchResponse,
} from "@/src/types/ai";
import { uuidToBytes32 } from "@/src/lib/ids";

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
  const rawPaymentToken = item.payment_token ?? item.paymentToken;
  if (typeof rawPaymentToken !== "string" || !rawPaymentToken.trim()) {
    throw new Error("Missing marketplace payment token from API.");
  }

  const SUPPORTED_CURRENCIES: MarketplaceSettlementCurrency[] = ["USDC", "CADC"];
  const rawCurrency = String(item.settlement_currency ?? "USDC").trim().toUpperCase();
  const settlementCurrency = SUPPORTED_CURRENCIES.includes(
    rawCurrency as MarketplaceSettlementCurrency,
  )
    ? (rawCurrency as MarketplaceSettlementCurrency)
    : "USDC";

  const EXPECTED_DECIMALS: Record<MarketplaceSettlementCurrency, number> = {
    USDC: 6,
    CADC: 18,
  };
  const settlementDecimals = Number(
    item.settlement_decimals ?? EXPECTED_DECIMALS[settlementCurrency],
  );

  const {
    price: _legacyPrice,
    paymentToken: _legacyPaymentToken,
    payment_token: _legacyPaymentTokenSnake,
    price_atomic: _legacyAtomic,
    settlement_currency: _legacyCurrency,
    settlement_decimals: _legacyDecimals,
    ...rest
  } = item;

  return {
    ...rest,
    payment_token: rawPaymentToken.trim(),
    price_atomic: normalizeAtomicString(priceAtomic),
    settlement_currency: settlementCurrency,
    settlement_decimals: settlementDecimals,
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
  ): Promise<SimilaritySearchResponse> => {
    const response = await apiRequest<RawSimilaritySearchResponse>(
      "/api/v1/ai/similarity-search",
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
    );

    return {
      ...response,
      results: response.results.map((result) => ({
        item: normalizeMarketplaceItem({
          id: uuidToBytes32(result.listing_id),
          title: result.title,
          description: result.description,
          seller: result.seller,
          payment_token: result.payment_token,
          price_atomic: result.price_atomic,
          settlement_currency: result.settlement_currency,
          settlement_decimals: result.settlement_decimals,
          dataset_url: "",
          dataset_hash: "0x",
          signature_url: "",
          signature_hash:
            "0x0000000000000000000000000000000000000000000000000000000000000000",
          exists: true,
          purchase_count: result.purchase_count,
        }),
        score: result.score,
        score_label: result.score_label,
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
      items: response.items.map(normalizeMarketplaceItem),
    };
  },
};
