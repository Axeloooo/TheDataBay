import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import RecordCard from "@/components/record-card";
import { backend } from "@/lib/backend";
import type { MarketplaceDataItem } from "@/types/contract";
import { useSearch } from "@/context/search-context";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import ErrorPanel from "@/components/ui/error-panel";
import { useWallet } from "@/providers/wallet-provider";
import { weiToEth } from "@/lib/marketplace";

function Home() {
  const [items, setItems] = useState<MarketplaceDataItem[]>([]);
  const [purchasedItems, setPurchasedItems] = useState<MarketplaceDataItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [purchasesError, setPurchasesError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingPurchases, setLoadingPurchases] = useState(false);
  const requestIdRef = useRef(0);
  const { address } = useWallet();

  const {
    submittedQuery,
    setResultCount,
    setIsSearching,
    clearSearch,
  } = useSearch();

  const loadItems = useCallback(async () => {
    const currentRequestId = ++requestIdRef.current;
    setLoading(true);
    setError(null);

    try {
      if (submittedQuery) {
        setIsSearching(true);
        const response = await backend.similaritySearch({ query: submittedQuery });
        if (currentRequestId !== requestIdRef.current) return;
        setItems(response.results.map((result) => result.item));
        setResultCount(response.count);
      } else {
        setIsSearching(false);
        const data = await backend.getMarketplaceItems();
        if (currentRequestId !== requestIdRef.current) return;
        setItems(data);
        setResultCount(data.length);
      }
    } catch (err) {
      if (currentRequestId !== requestIdRef.current) return;
      setItems([]);
      setResultCount(0);
      setError(
        err instanceof Error
          ? err.message
          : "We could not load marketplace items at the moment.",
      );
    } finally {
      if (currentRequestId !== requestIdRef.current) return;
      setLoading(false);
      setIsSearching(false);
    }
  }, [setIsSearching, setResultCount, submittedQuery]);

  useEffect(() => {
    void loadItems();
  }, [loadItems]);

  useEffect(() => {
    if (!address || submittedQuery) {
      setPurchasedItems([]);
      setPurchasesError(null);
      return;
    }
    let active = true;
    setLoadingPurchases(true);
    setPurchasesError(null);
    backend
      .getPurchasedItemsByWallet({
        wallet_type: "evm",
        address,
        limit: 12,
        offset: 0,
      })
      .then((response) => {
        if (!active) return;
        setPurchasedItems(response.items);
      })
      .catch((err) => {
        if (!active) return;
        setPurchasedItems([]);
        setPurchasesError(
          err instanceof Error ? err.message : "Failed to load your purchased datasets.",
        );
      })
      .finally(() => {
        if (!active) return;
        setLoadingPurchases(false);
      });
    return () => {
      active = false;
    };
  }, [address, submittedQuery]);

  return (
    <div className="min-h-screen">
      <div className="mx-auto w-full max-w-6xl px-4 py-6 space-y-4">
        {submittedQuery && !loading && !error && (
          <p className="text-sm text-muted-foreground">
            Showing semantic search results for{" "}
            <span className="font-medium text-foreground">"{submittedQuery}"</span>
          </p>
        )}

        {!submittedQuery && address && (
          <div className="rounded-xl border bg-card p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold">My Purchases</h2>
              <span className="text-xs text-muted-foreground">
                {loadingPurchases ? "Loading..." : `${purchasedItems.length} items`}
              </span>
            </div>
            {purchasesError ? (
              <p className="text-xs text-red-600">{purchasesError}</p>
            ) : loadingPurchases ? (
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {Array.from({ length: 3 }).map((_, idx) => (
                  <Skeleton key={idx} className="h-16 w-full" />
                ))}
              </div>
            ) : purchasedItems.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                No purchased datasets yet for this wallet.
              </p>
            ) : (
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {purchasedItems.slice(0, 6).map((item) => (
                  <Link
                    key={item.id}
                    to={`/dataset/${item.id}`}
                    className="rounded-md border p-2 text-xs hover:bg-accent"
                  >
                    <p className="font-medium line-clamp-1">{item.title}</p>
                    <p className="text-muted-foreground">{weiToEth(item.price)} ETH</p>
                  </Link>
                ))}
              </div>
            )}
          </div>
        )}

        {loading ? (
          <div className="grid gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {Array.from({ length: 8 }).map((_, index) => (
              <div key={index} className="rounded-xl border p-4 space-y-4">
                <Skeleton className="h-5 w-3/4" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-5/6" />
                <Skeleton className="h-4 w-2/3" />
                <Skeleton className="h-8 w-24" />
              </div>
            ))}
          </div>
        ) : error ? (
          <ErrorPanel
            title="Unable to load marketplace items"
            message={error}
            onRetry={() => void loadItems()}
          />
        ) : items.length === 0 ? (
          <div className="rounded-xl border bg-card p-8 text-center space-y-3">
            <h2 className="text-xl font-semibold">No datasets available yet</h2>
            <p className="text-sm text-muted-foreground">
              {submittedQuery
                ? "No semantic matches found. Try broader keywords or clear search."
                : "Publish your first dataset to start populating the marketplace."}
            </p>
            <div className="flex items-center justify-center gap-3">
              {submittedQuery && (
                <Button variant="outline" onClick={() => clearSearch()}>
                  Clear Search
                </Button>
              )}
              <Link to="/upload">
                <Button>Upload Dataset</Button>
              </Link>
            </div>
          </div>
        ) : (
          <div className="grid gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {items.map((item) => (
              <RecordCard
                key={item.id}
                id={item.id}
                title={item.title}
                description={item.description}
                priceEth={weiToEth(item.price)}
                purchaseCount={item.purchase_count}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default Home;
