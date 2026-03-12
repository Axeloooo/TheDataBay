import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  Database,
  Sparkles,
  TrendingUp,
  WalletCards,
  ArrowUpRight,
} from "lucide-react";
import RecordCard from "@/components/record-card";
import { backend } from "@/lib/backend";
import type { MarketplaceDataItem } from "@/types/contract";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import ErrorPanel from "@/components/ui/error-panel";
import { weiToEth } from "@/lib/marketplace";
import { useSearchStore } from "@/stores/search-store";
import { useWalletStore } from "@/stores/wallet-store";

function Home() {
  const [items, setItems] = useState<MarketplaceDataItem[]>([]);
  const [purchasedItems, setPurchasedItems] = useState<MarketplaceDataItem[]>(
    [],
  );
  const [error, setError] = useState<string | null>(null);
  const [purchasesError, setPurchasesError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingPurchases, setLoadingPurchases] = useState(false);
  const requestIdRef = useRef(0);
  const address = useWalletStore((state) => state.address);

  const submittedQuery = useSearchStore((state) => state.submittedQuery);
  const setResultCount = useSearchStore((state) => state.setResultCount);
  const setIsSearching = useSearchStore((state) => state.setIsSearching);
  const clearSearch = useSearchStore((state) => state.clearSearch);

  const loadItems = useCallback(async () => {
    const currentRequestId = ++requestIdRef.current;
    setLoading(true);
    setError(null);

    try {
      if (submittedQuery) {
        setIsSearching(true);
        const response = await backend.similaritySearch({
          query: submittedQuery,
        });
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
      if (currentRequestId === requestIdRef.current) {
        setLoading(false);
        setIsSearching(false);
      }
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
          err instanceof Error
            ? err.message
            : "Failed to load your purchased datasets.",
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
    <div className="space-y-6 pb-6">
      <section className="relative overflow-hidden rounded-3xl border border-border/75 bg-card/75 p-6 shadow-[0_25px_65px_-40px_rgba(15,24,47,0.65)] backdrop-blur md:p-8">
        <div className="pointer-events-none absolute -right-20 top-0 h-48 w-48 rounded-full bg-primary/25 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-14 left-1/3 h-48 w-48 rounded-full bg-chart-4/20 blur-3xl" />

        <div className="relative flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl space-y-3">
            <p className="inline-flex items-center gap-2 rounded-full border border-border/80 bg-background/65 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
              <Sparkles className="h-3.5 w-3.5" />
              Semantic data marketplace
            </p>
            <h1 className="text-balance text-3xl font-semibold leading-tight md:text-4xl">
              Discover verifiable datasets and unlock them with on-chain access.
            </h1>
            <p className="max-w-xl text-sm text-muted-foreground md:text-base">
              BridgeMart combines semantic search, encrypted IPFS delivery, and
              contract-based purchasing so teams can source AI-ready data with
              transparent provenance.
            </p>
          </div>

          <div className="grid w-full gap-3 sm:grid-cols-3 lg:w-auto lg:min-w-[420px]">
            <div className="rounded-2xl border border-border/70 bg-background/75 p-3">
              <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
                Visible listings
              </p>
              <p className="mt-1 text-2xl font-semibold">
                {loading ? "..." : items.length}
              </p>
            </div>
            <div className="rounded-2xl border border-border/70 bg-background/75 p-3">
              <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
                Purchased
              </p>
              <p className="mt-1 text-2xl font-semibold">
                {address
                  ? loadingPurchases
                    ? "..."
                    : purchasedItems.length
                  : "-"}
              </p>
            </div>
            <div className="rounded-2xl border border-border/70 bg-background/75 p-3">
              <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
                Settlement
              </p>
              <p className="mt-1 text-2xl font-semibold">ETH</p>
            </div>
          </div>
        </div>

        {submittedQuery && !loading && !error && (
          <div className="relative mt-5 flex flex-wrap items-center gap-2 rounded-2xl border border-primary/30 bg-primary/8 px-4 py-3 text-sm">
            <Database className="h-4 w-4 text-primary" />
            <span className="text-muted-foreground">
              Showing semantic matches for
            </span>
            <span className="font-semibold text-foreground">
              "{submittedQuery}"
            </span>
            <Button
              variant="ghost"
              className="ml-auto h-8 px-2 text-xs"
              onClick={() => clearSearch()}
            >
              Clear
            </Button>
          </div>
        )}
      </section>

      {!submittedQuery && address && (
        <section className="rounded-2xl border border-border/75 bg-card/65 p-4 backdrop-blur md:p-5">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
            <h2 className="inline-flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.08em] text-muted-foreground">
              <WalletCards className="h-4 w-4" />
              My Purchases
            </h2>
            <span className="text-xs text-muted-foreground">
              {loadingPurchases
                ? "Loading..."
                : `${purchasedItems.length} items`}
            </span>
          </div>

          {purchasesError ? (
            <p className="text-xs text-destructive">{purchasesError}</p>
          ) : loadingPurchases ? (
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 3 }).map((_, idx) => (
                <Skeleton key={idx} className="h-16 w-full rounded-xl" />
              ))}
            </div>
          ) : purchasedItems.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No purchased datasets yet for this wallet.
            </p>
          ) : (
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {purchasedItems.slice(0, 6).map((item) => (
                <Link
                  key={item.id}
                  to={`/dataset/${item.id}`}
                  className="group rounded-xl border border-border/75 bg-background/70 p-3 text-xs transition hover:border-primary/50 hover:bg-background"
                >
                  <p className="font-semibold line-clamp-1">{item.title}</p>
                  <p className="mt-1 text-muted-foreground">
                    {weiToEth(item.price)} ETH
                  </p>
                  <p className="mt-2 inline-flex items-center gap-1 text-primary">
                    Open listing
                    <ArrowUpRight className="h-3.5 w-3.5" />
                  </p>
                </Link>
              ))}
            </div>
          )}
        </section>
      )}

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="inline-flex items-center gap-2 text-lg font-semibold">
            <TrendingUp className="h-5 w-5 text-primary" />
            Marketplace Listings
          </h2>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {Array.from({ length: 8 }).map((_, index) => (
              <div
                key={index}
                className="rounded-2xl border border-border/70 bg-card/70 p-4 space-y-4"
              >
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
          <div className="rounded-2xl border border-border/75 bg-card/60 p-8 text-center space-y-3">
            <h2 className="text-2xl font-semibold">
              No datasets available yet
            </h2>
            <p className="mx-auto max-w-lg text-sm text-muted-foreground">
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
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
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
      </section>
    </div>
  );
}

export default Home;
