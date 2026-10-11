import { create } from "zustand";
import { backend } from "@/src/lib/backend";
import type { PurchasedListing, SellerListing } from "@/src/types/me";

type MeStore = {
  purchases: PurchasedListing[];
  purchasesLoading: boolean;
  purchasesLoaded: boolean;
  purchasesError: string | null;
  listings: SellerListing[];
  listingsLoading: boolean;
  listingsLoaded: boolean;
  listingsError: string | null;
  fetchPurchases: () => Promise<void>;
  fetchListings: () => Promise<void>;
  clear: () => void;
};

const empty = (): Pick<
  MeStore,
  | "purchases"
  | "purchasesLoading"
  | "purchasesLoaded"
  | "purchasesError"
  | "listings"
  | "listingsLoading"
  | "listingsLoaded"
  | "listingsError"
> => ({
  purchases: [],
  purchasesLoading: false,
  purchasesLoaded: false,
  purchasesError: null,
  listings: [],
  listingsLoading: false,
  listingsLoaded: false,
  listingsError: null,
});

export const useMeStore = create<MeStore>()((set, get) => ({
  ...empty(),

  fetchPurchases: async () => {
    if (get().purchasesLoading) return;
    set({ purchasesLoading: true, purchasesError: null });
    try {
      const purchases = await backend.getMyPurchases();
      set({ purchases, purchasesLoading: false, purchasesLoaded: true });
    } catch (error) {
      set({
        purchasesLoading: false,
        purchasesError:
          error instanceof Error ? error.message : "Failed to load datasets",
      });
    }
  },

  fetchListings: async () => {
    if (get().listingsLoading) return;
    set({ listingsLoading: true, listingsError: null });
    try {
      const listings = await backend.getMyListings();
      set({ listings, listingsLoading: false, listingsLoaded: true });
    } catch (error) {
      set({
        listingsLoading: false,
        listingsError:
          error instanceof Error ? error.message : "Failed to load listings",
      });
    }
  },

  clear: () => set({ ...empty() }),
}));
