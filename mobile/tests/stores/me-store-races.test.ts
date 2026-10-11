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

const purchase = {
  listing_id: "0x01",
  title: "A",
  description: "d",
  dataset_url: "ipfs://cid",
  price_paid: "1",
  payment_token: "0x0A",
  token_symbol: "USDC",
  token_decimals: 6,
  purchased_at: null,
  source: "indexer",
} as PurchasedListing;

const listing = {
  listing_id: "0x02",
  title: "L",
  price: "1",
  payment_token: "0x0A",
  token_symbol: "USDC",
  token_decimals: 6,
  sales_count: 0,
  earnings_by_token: {},
  price_editable: true,
  source: "indexer",
} as SellerListing;

function deferred<T>() {
  let resolve!: (v: T) => void;
  let reject!: (e: Error) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

beforeEach(() => {
  jest.clearAllMocks();
  useMeStore.getState().clear();
});

describe("me-store wallet races", () => {
  it("drops a late purchases response from the previous wallet after clear", async () => {
    const a = deferred<PurchasedListing[]>();
    mockBackend.getMyPurchases.mockReturnValueOnce(a.promise);
    const pendingA = useMeStore.getState().fetchPurchases();
    useMeStore.getState().clear(); // wallet switch or disconnect
    a.resolve([purchase]);
    await pendingA;
    expect(useMeStore.getState().purchases).toEqual([]);
    expect(useMeStore.getState().purchasesLoaded).toBe(false);
  });

  it("does not let wallet A's in-flight fetch block or overwrite wallet B's", async () => {
    const a = deferred<PurchasedListing[]>();
    mockBackend.getMyPurchases.mockReturnValueOnce(a.promise);
    const pendingA = useMeStore.getState().fetchPurchases();
    useMeStore.getState().clear();
    mockBackend.getMyPurchases.mockResolvedValueOnce([]);
    await useMeStore.getState().fetchPurchases();
    expect(mockBackend.getMyPurchases).toHaveBeenCalledTimes(2);
    a.resolve([purchase]);
    await pendingA;
    expect(useMeStore.getState().purchases).toEqual([]);
    expect(useMeStore.getState().purchasesLoaded).toBe(true);
    expect(useMeStore.getState().purchasesLoading).toBe(false);
  });

  it("drops a late listings response after clear", async () => {
    const a = deferred<SellerListing[]>();
    mockBackend.getMyListings.mockReturnValueOnce(a.promise);
    const pendingA = useMeStore.getState().fetchListings();
    useMeStore.getState().clear();
    a.resolve([listing]);
    await pendingA;
    expect(useMeStore.getState().listings).toEqual([]);
  });

  it("drops a late error after clear", async () => {
    const a = deferred<SellerListing[]>();
    mockBackend.getMyListings.mockReturnValueOnce(a.promise);
    const pendingA = useMeStore.getState().fetchListings();
    useMeStore.getState().clear();
    a.reject(new Error("late"));
    await pendingA;
    expect(useMeStore.getState().listingsError).toBeNull();
    expect(useMeStore.getState().listingsLoading).toBe(false);
  });
});
