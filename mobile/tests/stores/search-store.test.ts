import { act } from "react";
import { useSearchStore } from "../../src/stores/search-store";

// Reset store state between tests
beforeEach(() => {
  useSearchStore.setState({
    query: "",
    submittedQuery: "",
    resultCount: null,
    isSearching: false,
    error: null,
    results: [],
  });
});

describe("useSearchStore", () => {
  describe("setQuery", () => {
    it("sets the query", () => {
      act(() => {
        useSearchStore.getState().setQuery("climate data");
      });
      expect(useSearchStore.getState().query).toBe("climate data");
    });
  });

  describe("submitSearch", () => {
    it("trims and sets submittedQuery", () => {
      act(() => {
        useSearchStore.getState().setQuery("  test query  ");
        useSearchStore.getState().submitSearch();
      });
      expect(useSearchStore.getState().submittedQuery).toBe("test query");
    });

    it("does not set submittedQuery for empty string", () => {
      act(() => {
        useSearchStore.getState().setQuery("   ");
        useSearchStore.getState().submitSearch();
      });
      expect(useSearchStore.getState().submittedQuery).toBe("");
    });

    it("clears resultCount when query is empty", () => {
      act(() => {
        useSearchStore.getState().setResultCount(42);
        useSearchStore.getState().setQuery("");
        useSearchStore.getState().submitSearch();
      });
      expect(useSearchStore.getState().resultCount).toBeNull();
    });
  });

  describe("clearSearch", () => {
    it("resets all fields", () => {
      act(() => {
        useSearchStore.getState().setQuery("test");
        useSearchStore.getState().submitSearch();
        useSearchStore.getState().setResultCount(10);
        useSearchStore.getState().setIsSearching(true);
        useSearchStore.getState().clearSearch();
      });
      const state = useSearchStore.getState();
      expect(state.query).toBe("");
      expect(state.submittedQuery).toBe("");
      expect(state.resultCount).toBeNull();
      expect(state.isSearching).toBe(false);
    });
  });

  describe("setResultCount", () => {
    it("sets result count", () => {
      act(() => {
        useSearchStore.getState().setResultCount(7);
      });
      expect(useSearchStore.getState().resultCount).toBe(7);
    });

    it("accepts null", () => {
      act(() => {
        useSearchStore.getState().setResultCount(null);
      });
      expect(useSearchStore.getState().resultCount).toBeNull();
    });
  });
});
