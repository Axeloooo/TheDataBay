import { createContext, useContext, useMemo, useState } from "react";

type SearchContextValue = {
  query: string;
  submittedQuery: string;
  resultCount: number | null;
  isSearching: boolean;
  setQuery: (value: string) => void;
  submitSearch: () => void;
  clearSearch: () => void;
  setResultCount: (count: number | null) => void;
  setIsSearching: (value: boolean) => void;
};

const SearchContext = createContext<SearchContextValue | null>(null);

export function SearchProvider({ children }: { children: React.ReactNode }) {
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [resultCount, setResultCount] = useState<number | null>(null);
  const [isSearching, setIsSearching] = useState(false);

  const submitSearch = () => {
    const normalized = query.trim();
    setSubmittedQuery(normalized);
    if (!normalized) {
      setResultCount(null);
      setIsSearching(false);
    }
  };

  const clearSearch = () => {
    setQuery("");
    setSubmittedQuery("");
    setResultCount(null);
    setIsSearching(false);
  };

  const value = useMemo(
    () => ({
      query,
      submittedQuery,
      resultCount,
      isSearching,
      setQuery,
      submitSearch,
      clearSearch,
      setResultCount,
      setIsSearching,
    }),
    [query, submittedQuery, resultCount, isSearching],
  );

  return <SearchContext.Provider value={value}>{children}</SearchContext.Provider>;
}

export function useSearch() {
  const ctx = useContext(SearchContext);
  if (!ctx) throw new Error("useSearch must be used within SearchProvider");
  return ctx;
}
