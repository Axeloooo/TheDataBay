import { create } from "zustand";

type SearchStore = {
  query: string;
  submittedQuery: string;
  resultCount: number | null;
  isSearching: boolean;
  setQuery: (value: string) => void;
  submitSearch: () => void;
  clearSearch: () => void;
  setResultCount: (count: number | null) => void;
  setIsSearching: (value: boolean) => void;
  resetOnAppStart: () => void;
};

export const useSearchStore = create<SearchStore>()((set, get) => ({
  query: "",
  submittedQuery: "",
  resultCount: null,
  isSearching: false,
  setQuery: (value) => set({ query: value }),
  submitSearch: () => {
    const normalized = get().query.trim();
    if (!normalized) {
      set({ submittedQuery: "", resultCount: null, isSearching: false });
      return;
    }
    set({ submittedQuery: normalized });
  },
  clearSearch: () =>
    set({
      query: "",
      submittedQuery: "",
      resultCount: null,
      isSearching: false,
    }),
  setResultCount: (count) => set({ resultCount: count }),
  setIsSearching: (value) => set({ isSearching: value }),
  resetOnAppStart: () =>
    set({
      query: "",
      submittedQuery: "",
      resultCount: null,
      isSearching: false,
    }),
}));
