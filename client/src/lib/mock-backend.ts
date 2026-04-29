import type { MarketplaceDataItem, AccessCheckResponse, PurchasedItemsRequest, PurchasedItemsResponse } from "@/types/contract";
import type {
  DatasetEmbedResponse,
  KeyReleaseResponse,
} from "@/types/dataset";
import type { CardViewModel, SimilaritySearchRequest, ScoreLabel } from "@/types/ai";
import type { Agent, AgentListResponse, RecommendationListResponse, PurchaseRequest, PurchaseRequestListResponse } from "@/types/agent";
import {
  MOCK_ITEMS,
  MOCK_AGENTS,
  MOCK_RECOMMENDATIONS,
  MOCK_PURCHASE_REQUESTS,
  MOCK_PURCHASED_IDS,
} from "@/lib/mock-data";
import { uuidToBytes32 } from "@/lib/ids";

function delay<T>(data: T, ms = 250): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(data), ms));
}

function withBytes32Id(item: MarketplaceDataItem): MarketplaceDataItem {
  return { ...item, id: uuidToBytes32(item.id) };
}

export const mockBackend = {
  submitDataset: (): Promise<DatasetEmbedResponse> => {
    return Promise.reject(new Error("Upload is not available in demo mode."));
  },

  getMarketplaceItems: (): Promise<MarketplaceDataItem[]> => {
    return delay(MOCK_ITEMS.map(withBytes32Id));
  },

  getMarketplaceItem: (listingId: string): Promise<MarketplaceDataItem> => {
    const item = MOCK_ITEMS.find((i) => i.id === listingId);
    if (!item) return Promise.reject(new Error(`Item ${listingId} not found.`));
    return delay({ ...item });
  },

  requestKeyRelease: (): Promise<KeyReleaseResponse> => {
    return Promise.reject(new Error("Key release is not available in demo mode."));
  },

  checkAccess: (listingId: string): Promise<AccessCheckResponse> => {
    return delay({ has_access: MOCK_PURCHASED_IDS.has(listingId) });
  },

  getDatasetPreview: (): Promise<{ column_names: string[]; rows: string[][] }> => {
    return delay({
      column_names: ["age", "sex", "cp", "trestbps", "chol", "fbs", "restecg", "thalach", "exang", "num"],
      rows: [
        ["63", "1", "3", "145", "233", "1", "0", "150", "0", "1"],
        ["37", "1", "2", "130", "250", "0", "1", "187", "0", "0"],
        ["41", "0", "1", "130", "204", "0", "0", "172", "0", "0"],
      ],
    });
  },

  similaritySearch: (
    payload: SimilaritySearchRequest,
  ): Promise<{ query: string; results: CardViewModel[]; count: number }> => {
    const q = payload.query.toLowerCase();
    const results = MOCK_ITEMS
      .filter((item) =>
        item.title.toLowerCase().includes(q) ||
        item.description.toLowerCase().includes(q)
      )
      .map((item): CardViewModel => {
        const score = item.title.toLowerCase().includes(q) ? 0.95 : 0.72;
        const scoreLabel: ScoreLabel = score >= 0.9 ? "high" : score >= 0.7 ? "moderate" : "low";
        return {
          dataset: {
            id: uuidToBytes32(item.id),
            title: item.title,
            description: item.description,
            payment_token: item.payment_token,
            price_atomic: String(item.price_atomic ?? 0),
            settlement_currency: item.settlement_currency ?? "USDC",
            settlement_decimals: item.settlement_decimals ?? 6,
            purchase_count: item.purchase_count ?? 0,
          },
          score,
          scoreLabel,
        };
      });
    return delay({ query: payload.query, results, count: results.length });
  },

  getPurchasedItemsByWallet: (payload: PurchasedItemsRequest): Promise<PurchasedItemsResponse> => {
    const items = MOCK_ITEMS.filter((i) => MOCK_PURCHASED_IDS.has(i.id)).map(withBytes32Id);
    return delay({ wallet_id: payload.address, items, count: items.length });
  },

  getAgents: (params?: { search?: string; tag?: string; status?: string; offset?: number; limit?: number }): Promise<AgentListResponse> => {
    let filtered = [...MOCK_AGENTS];
    if (params?.search) {
      const s = params.search.toLowerCase();
      filtered = filtered.filter(
        (a) => a.handle.toLowerCase().includes(s) || a.display_name.toLowerCase().includes(s)
      );
    }
    if (params?.tag) {
      filtered = filtered.filter((a) => a.capability_tags.includes(params.tag!));
    }
    if (params?.status) {
      filtered = filtered.filter((a) => a.verification_status === params.status);
    }
    const total = filtered.length;
    const offset = params?.offset ?? 0;
    const limit = params?.limit ?? 20;
    filtered = filtered.slice(offset, offset + limit);
    return delay({ agents: filtered, count: filtered.length, total });
  },

  getAgent: (handle: string): Promise<Agent> => {
    const agent = MOCK_AGENTS.find((a) => a.handle === handle);
    if (!agent) return Promise.reject(new Error(`Agent ${handle} not found.`));
    return delay({ ...agent });
  },

  getAgentRecommendations: (handle: string, params?: { offset?: number; limit?: number }): Promise<RecommendationListResponse> => {
    const agent = MOCK_AGENTS.find((a) => a.handle === handle);
    if (!agent) return Promise.reject(new Error(`Agent ${handle} not found.`));
    let recs = MOCK_RECOMMENDATIONS.filter((r) => r.agent_id === agent.id);
    const total = recs.length;
    const offset = params?.offset ?? 0;
    const limit = params?.limit ?? 20;
    recs = recs.slice(offset, offset + limit);
    return delay({ recommendations: recs, count: recs.length, total });
  },

  getRecommendationsForListing: (listingId: string): Promise<RecommendationListResponse> => {
    const recs = MOCK_RECOMMENDATIONS.filter((r) => r.listing_id === listingId);
    return delay({ recommendations: recs, count: recs.length, total: recs.length });
  },

  getPurchaseRequests: (params?: { status?: string; offset?: number; limit?: number }): Promise<PurchaseRequestListResponse> => {
    let filtered = [...MOCK_PURCHASE_REQUESTS];
    if (params?.status) {
      filtered = filtered.filter((r) => r.status === params.status);
    }
    const total = filtered.length;
    const offset = params?.offset ?? 0;
    const limit = params?.limit ?? 20;
    filtered = filtered.slice(offset, offset + limit);
    return delay({ requests: filtered, count: filtered.length, total });
  },

  reviewPurchaseRequest: (requestId: string, payload: { status: "approved" | "rejected"; reviewed_by: string }): Promise<PurchaseRequest> => {
    const idx = MOCK_PURCHASE_REQUESTS.findIndex((r) => r.id === requestId);
    if (idx === -1) return Promise.reject(new Error(`Purchase request ${requestId} not found.`));
    MOCK_PURCHASE_REQUESTS[idx] = {
      ...MOCK_PURCHASE_REQUESTS[idx],
      status: payload.status,
      reviewed_by: payload.reviewed_by,
      reviewed_at: new Date().toISOString(),
    };
    return delay({ ...MOCK_PURCHASE_REQUESTS[idx] });
  },
};
