import { create } from "zustand";
import { backend } from "@/src/lib/backend";
import type { MarketplaceDataItem } from "@/src/types/contract";

const CACHE_TTL_MS = 60_000;

type MarketplaceStore = {
  items: MarketplaceDataItem[];
  purchases: MarketplaceDataItem[];
  loading: boolean;
  purchasesLoading: boolean;
  error: string | null;
  purchasesError: string | null;
  lastFetchedAt: number | null;
  lastPurchasesFetchedAt: number | null;
  lastPurchasesAddress: string | null;
  fetchItems: (force?: boolean) => Promise<void>;
  fetchPurchases: (address: string, force?: boolean) => Promise<void>;
  clearPurchases: () => void;
};

export const useMarketplaceStore = create<MarketplaceStore>()((set, get) => ({
  items: [],
  purchases: [],
  loading: false,
  purchasesLoading: false,
  error: null,
  purchasesError: null,
  lastFetchedAt: null,
  lastPurchasesFetchedAt: null,
  lastPurchasesAddress: null,

  fetchItems: async (force = false) => {
    const { lastFetchedAt, loading } = get();

    if (loading) return;

    if (!force && lastFetchedAt && Date.now() - lastFetchedAt < CACHE_TTL_MS) {
      return;
    }

    set({ loading: true, error: null });
    try {
      const items = await backend.getMarketplaceItems();
      set({ items, loading: false, lastFetchedAt: Date.now() });
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to load marketplace";
      set({ loading: false, error: message });
    }
  },

  fetchPurchases: async (address, force = false) => {
    const normalizedAddress = address.trim().toLowerCase();
    const {
      purchasesLoading,
      lastPurchasesFetchedAt,
      lastPurchasesAddress,
      purchases,
    } = get();

    if (!normalizedAddress) {
      set({
        purchases: [],
        purchasesLoading: false,
        purchasesError: null,
        lastPurchasesFetchedAt: null,
        lastPurchasesAddress: null,
      });
      return;
    }

    if (purchasesLoading && lastPurchasesAddress === normalizedAddress) {
      return;
    }

    if (
      !force &&
      purchases.length > 0 &&
      lastPurchasesAddress === normalizedAddress &&
      lastPurchasesFetchedAt &&
      Date.now() - lastPurchasesFetchedAt < CACHE_TTL_MS
    ) {
      return;
    }

    set({
      purchasesLoading: true,
      purchasesError: null,
      purchases: lastPurchasesAddress === normalizedAddress ? purchases : [],
      lastPurchasesAddress: normalizedAddress,
    });

    try {
      const response = await backend.getPurchasedItemsByWallet({
        wallet_type: "evm",
        address: normalizedAddress,
        limit: 12,
        offset: 0,
      });

      // Ignore stale responses from previous wallet requests.
      if (get().lastPurchasesAddress !== normalizedAddress) {
        return;
      }

      set({
        purchases: response.items,
        purchasesLoading: false,
        purchasesError: null,
        lastPurchasesFetchedAt: Date.now(),
        lastPurchasesAddress: normalizedAddress,
      });
    } catch (error) {
      if (get().lastPurchasesAddress !== normalizedAddress) {
        return;
      }

      const message =
        error instanceof Error
          ? error.message
          : "Failed to load purchased datasets";

      set({
        purchasesLoading: false,
        purchasesError: message,
      });
    }
  },

  clearPurchases: () => {
    set({
      purchases: [],
      purchasesLoading: false,
      purchasesError: null,
      lastPurchasesFetchedAt: null,
      lastPurchasesAddress: null,
    });
  },
}));
