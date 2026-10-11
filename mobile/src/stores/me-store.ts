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

// Bumped by clear() (wallet switch or disconnect). A request started under an
// older generation belongs to a previous wallet, so its result is discarded
// and it never touches the loading flags of the current wallet's request.
let generation = 0;

export const useMeStore = create<MeStore>()((set, get) => ({
  ...empty(),

  fetchPurchases: async () => {
    if (get().purchasesLoading) return;
    const started = generation;
    set({ purchasesLoading: true, purchasesError: null });
    try {
      const purchases = await backend.getMyPurchases();
      if (started !== generation) return;
      set({ purchases, purchasesLoading: false, purchasesLoaded: true });
    } catch (error) {
      if (started !== generation) return;
      set({
        purchasesLoading: false,
        purchasesError:
          error instanceof Error ? error.message : "Failed to load datasets",
      });
    }
  },

  fetchListings: async () => {
    if (get().listingsLoading) return;
    const started = generation;
    set({ listingsLoading: true, listingsError: null });
    try {
      const listings = await backend.getMyListings();
      if (started !== generation) return;
      set({ listings, listingsLoading: false, listingsLoaded: true });
    } catch (error) {
      if (started !== generation) return;
      set({
        listingsLoading: false,
        listingsError:
          error instanceof Error ? error.message : "Failed to load listings",
      });
    }
  },

  clear: () => {
    generation += 1;
    set({ ...empty() });
  },
}));
