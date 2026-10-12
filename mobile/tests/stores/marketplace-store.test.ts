import { act } from "react";
import { useMarketplaceStore } from "../../src/stores/marketplace-store";
import type { MarketplaceDataItem } from "../../src/types/contract";

// Mock the backend module
jest.mock("../../src/lib/backend", () => ({
  backend: {
    getMarketplaceItems: jest.fn(),
  },
}));

import { backend } from "../../src/lib/backend";
const mockBackend = backend as jest.Mocked<typeof backend>;

const mockItems: MarketplaceDataItem[] = [
  {
    id: "550e8400-e29b-41d4-a716-446655440000",
    title: "Test Dataset",
    description: "A test dataset",
    seller: "0xdeadbeef",
    payment_token: "0x0000000000000000000000000000000000000001",
    price_atomic: "1000000",
    settlement_currency: "USDC",
    settlement_decimals: 6,
    dataset_url: "ipfs://QmTest",
    dataset_hash: "0xabc",
    signature_url: "ipfs://QmSig",
    signature_hash: "0xdef",
    exists: true,
    purchase_count: 5,
  },
];

beforeEach(() => {
  useMarketplaceStore.setState({
    items: [],
    loading: false,
    error: null,
    lastFetchedAt: null,
  });
  jest.clearAllMocks();
});

describe("useMarketplaceStore", () => {
  describe("fetchItems", () => {
    it("fetches items and sets them in state", async () => {
      mockBackend.getMarketplaceItems.mockResolvedValueOnce(mockItems);

      await act(async () => {
        await useMarketplaceStore.getState().fetchItems();
      });

      const state = useMarketplaceStore.getState();
      expect(state.items).toEqual(mockItems);
      expect(state.loading).toBe(false);
      expect(state.error).toBeNull();
      expect(state.lastFetchedAt).not.toBeNull();
    });

    it("sets error state on fetch failure", async () => {
      mockBackend.getMarketplaceItems.mockRejectedValueOnce(
        new Error("Network error"),
      );

      await act(async () => {
        await useMarketplaceStore.getState().fetchItems();
      });

      const state = useMarketplaceStore.getState();
      expect(state.items).toEqual([]);
      expect(state.loading).toBe(false);
      expect(state.error).toBe("Network error");
    });

    it("skips re-fetch within TTL", async () => {
      mockBackend.getMarketplaceItems.mockResolvedValue(mockItems);

      // First fetch
      await act(async () => {
        await useMarketplaceStore.getState().fetchItems();
      });

      // Second fetch within TTL should be skipped
      await act(async () => {
        await useMarketplaceStore.getState().fetchItems();
      });

      expect(mockBackend.getMarketplaceItems).toHaveBeenCalledTimes(1);
    });

    it("forces re-fetch when force=true", async () => {
      mockBackend.getMarketplaceItems.mockResolvedValue(mockItems);

      await act(async () => {
        await useMarketplaceStore.getState().fetchItems();
      });

      await act(async () => {
        await useMarketplaceStore.getState().fetchItems(true);
      });

      expect(mockBackend.getMarketplaceItems).toHaveBeenCalledTimes(2);
    });
  });
});
