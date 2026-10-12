import { useMeStore } from "../../src/stores/me-store";
import type { PurchasedListing, SellerListing } from "../../src/types/me";

jest.mock("../../src/lib/backend", () => ({
  backend: {
    getMyPurchases: jest.fn(),
    getMyListings: jest.fn(),
  },
}));

import { backend } from "../../src/lib/backend";
const mockBackend = backend as jest.Mocked<typeof backend>;

const purchase: PurchasedListing = {
  listing_id: "0x" + "01".repeat(16) + "00".repeat(16),
  title: "Climate Data",
  description: "Temperature anomalies",
  dataset_url: "ipfs://cid",
  price_paid: "1010000",
  payment_token: "0x0A",
  token_symbol: "USDC",
  token_decimals: 6,
  purchased_at: "2026-10-11T00:00:00Z",
  source: "indexer",
};

const listing: SellerListing = {
  listing_id: "0x" + "02".repeat(16) + "00".repeat(16),
  title: "Sold set",
  price: "5000000",
  payment_token: "0x0A",
  token_symbol: "USDC",
  token_decimals: 6,
  sales_count: 2,
  earnings_by_token: { "0x0A": "2000000" },
  price_editable: false,
  source: "indexer",
};

beforeEach(() => {
  jest.clearAllMocks();
  useMeStore.getState().clear();
});

describe("me-store purchases", () => {
  it("is loading while the request is in flight, then holds the rows", async () => {
    let resolve!: (rows: PurchasedListing[]) => void;
    mockBackend.getMyPurchases.mockReturnValue(
      new Promise((r) => {
        resolve = r;
      }),
    );
    const pending = useMeStore.getState().fetchPurchases();
    expect(useMeStore.getState().purchasesLoading).toBe(true);
    resolve([purchase]);
    await pending;
    const state = useMeStore.getState();
    expect(state.purchasesLoading).toBe(false);
    expect(state.purchases).toEqual([purchase]);
    expect(state.purchasesError).toBeNull();
  });

  it("keeps an empty list for a wallet with no purchases", async () => {
    mockBackend.getMyPurchases.mockResolvedValue([]);
    await useMeStore.getState().fetchPurchases();
    expect(useMeStore.getState().purchases).toEqual([]);
    expect(useMeStore.getState().purchasesLoaded).toBe(true);
  });

  it("records the error message and clears loading on failure", async () => {
    mockBackend.getMyPurchases.mockRejectedValue(new Error("boom"));
    await useMeStore.getState().fetchPurchases();
    const state = useMeStore.getState();
    expect(state.purchasesError).toBe("boom");
    expect(state.purchasesLoading).toBe(false);
  });
});

describe("me-store listings", () => {
  it("loads seller listings", async () => {
    mockBackend.getMyListings.mockResolvedValue([listing]);
    await useMeStore.getState().fetchListings();
    const state = useMeStore.getState();
    expect(state.listings).toEqual([listing]);
    expect(state.listingsLoading).toBe(false);
    expect(state.listingsError).toBeNull();
  });

  it("keeps an empty list for a wallet with no listings", async () => {
    mockBackend.getMyListings.mockResolvedValue([]);
    await useMeStore.getState().fetchListings();
    expect(useMeStore.getState().listings).toEqual([]);
    expect(useMeStore.getState().listingsLoaded).toBe(true);
  });

  it("records the error message on failure", async () => {
    mockBackend.getMyListings.mockRejectedValue(new Error("nope"));
    await useMeStore.getState().fetchListings();
    expect(useMeStore.getState().listingsError).toBe("nope");
  });

  it("clear drops rows from a previous wallet", async () => {
    mockBackend.getMyListings.mockResolvedValue([listing]);
    await useMeStore.getState().fetchListings();
    useMeStore.getState().clear();
    expect(useMeStore.getState().listings).toEqual([]);
    expect(useMeStore.getState().listingsLoaded).toBe(false);
  });
});
