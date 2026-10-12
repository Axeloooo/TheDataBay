import { create } from "zustand";

import { backend } from "@/src/lib/backend";
import type { RankedDataset } from "@/src/types/ai";

type SearchStore = {
  query: string;
  submittedQuery: string;
  resultCount: number | null;
  isSearching: boolean;
  error: string | null;
  results: RankedDataset[];
  setQuery: (value: string) => void;
  setResultCount: (value: number | null) => void;
  setIsSearching: (value: boolean) => void;
  submitSearch: () => Promise<void>;
  clearSearch: () => void;
  hydrateSearch: (query: string) => Promise<void>;
};

export const useSearchStore = create<SearchStore>()((set, get) => ({
  query: "",
  submittedQuery: "",
  resultCount: null,
  isSearching: false,
  error: null,
  results: [],

  setQuery: (value) => set({ query: value }),
  setResultCount: (value) => set({ resultCount: value }),
  setIsSearching: (value) => set({ isSearching: value }),

  async submitSearch() {
    const normalized = get().query.trim();

    if (!normalized) {
      set({
        submittedQuery: "",
        resultCount: null,
        isSearching: false,
        error: null,
        results: [],
      });
      return;
    }

    set({
      submittedQuery: normalized,
      isSearching: true,
      error: null,
    });

    try {
      const response = await backend.similaritySearch({ query: normalized });
      set({
        results: response.results,
        resultCount: response.count,
        isSearching: false,
        error: null,
      });
    } catch (error) {
      set({
        results: [],
        resultCount: 0,
        isSearching: false,
        error: error instanceof Error ? error.message : "Search failed.",
      });
    }
  },

  clearSearch() {
    set({
      query: "",
      submittedQuery: "",
      resultCount: null,
      isSearching: false,
      error: null,
      results: [],
    });
  },

  async hydrateSearch(query) {
    set({ query });
    await get().submitSearch();
  },
}));
