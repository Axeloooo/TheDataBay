import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Pencil, Wallet } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import ErrorPanel from "@/components/ui/error-panel";
import { Skeleton } from "@/components/ui/skeleton";
import { backend } from "@/lib/backend";
import { formatAtomicAmount } from "@/lib/marketplace";
import { useWalletStore } from "@/stores/wallet-store";
import type { SellerListing } from "@/types/me";

type TokenTotal = { symbol: string; decimals: number; total: bigint };

/**
 * Sum earnings per token address. Each token carries its own symbol and
 * decimals, taken from a listing that is actually priced in that token.
 */
function earningsTotals(listings: SellerListing[]): TokenTotal[] {
  const meta = new Map<string, { symbol: string; decimals: number }>();
  for (const listing of listings) {
    meta.set(listing.payment_token.toLowerCase(), {
      symbol: listing.token_symbol,
      decimals: listing.token_decimals,
    });
  }
  const totals = new Map<string, TokenTotal>();
  for (const listing of listings) {
    for (const [token, amount] of Object.entries(listing.earnings_by_token)) {
      const id = token.toLowerCase();
      const info = meta.get(id) ?? { symbol: token, decimals: 0 };
      const current = totals.get(id) ?? { ...info, total: 0n };
      current.total += BigInt(amount);
      totals.set(id, current);
    }
  }
  return [...totals.values()];
}

function SellerDashboard() {
  const isConnected = useWalletStore((state) => state.isConnected);
  const address = useWalletStore((state) => state.address);

  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<{
    key: string;
    rows?: SellerListing[];
    error?: string;
  } | null>(null);

  // Results are tied to the wallet and attempt that requested them, so a
  // different wallet never sees the previous wallet's rows.
  const key = `${address ?? ""}:${attempt}`;
  const current = result?.key === key ? result : null;
  const listings = current?.rows ?? null;
  const error = current?.error ?? null;

  const retry = () => setAttempt((n) => n + 1);

  useEffect(() => {
    if (!isConnected || !address) return;
    let cancelled = false;
    backend
      .getMyListings()
      .then((rows) => {
        if (!cancelled) setResult({ key, rows });
      })
      .catch((err: unknown) => {
        if (!cancelled)
          setResult({
            key,
            error: err instanceof Error ? err.message : "Failed to load listings.",
          });
      });
    return () => {
      cancelled = true;
    };
  }, [isConnected, address, key]);


  if (!isConnected) {
    return (
      <div className="mx-auto flex min-h-[50vh] w-full max-w-2xl flex-col items-center justify-center gap-3 px-4 py-8 text-center">
        <Wallet className="h-8 w-8" />
        <h1 className="text-2xl font-bold">Seller dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Connect your wallet to see your listings and earnings.
        </p>
        <Link to="/">
          <Button variant="outline">Back to marketplace</Button>
        </Link>
      </div>
    );
  }

  const totals = listings ? earningsTotals(listings) : [];
  const contractOnly =
    listings !== null &&
    listings.length > 0 &&
    listings.every((l) => l.source === "contract");

  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-8">
      <h1 className="text-2xl font-bold">Seller dashboard</h1>
      <p className="mt-1 mb-6 text-sm text-muted-foreground">
        Your listings, sales and earnings per payment token.
      </p>

      {error && (
        <ErrorPanel
          title="Could not load your listings"
          message={error}
          onRetry={retry}
        />
      )}

      {!error && listings === null && (
        <div className="space-y-3" data-testid="seller-loading">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      )}

      {!error && listings !== null && listings.length === 0 && (
        <div className="rounded-xl border p-8 text-center">
          <p className="font-medium">You haven't listed any datasets yet.</p>
          <Link to="/upload">
            <Button className="mt-4">List a dataset</Button>
          </Link>
        </div>
      )}

      {!error && listings !== null && listings.length > 0 && (
        <>
          <div className="mb-4 rounded-xl border p-4">
            <h2 className="text-sm font-semibold">Total earnings</h2>
            {contractOnly ? (
              <p className="mt-1 text-sm text-muted-foreground">
                Earnings are unavailable until the marketplace indexer is
                synced. Sales counts below are still accurate.
              </p>
            ) : totals.length === 0 ? (
              <p className="mt-1 text-sm text-muted-foreground">No sales yet.</p>
            ) : (
              <ul className="mt-1 text-sm">
                {totals.map((t) => (
                  <li key={t.symbol}>
                    {formatAtomicAmount(t.total, t.decimals)} {t.symbol}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <ul className="space-y-3">
            {listings.map((listing) => (
              <li key={listing.listing_id}>
                <Card>
                  <CardHeader>
                    <CardTitle>
                      <Link
                        to={`/dataset/${listing.listing_id}`}
                        className="hover:underline"
                      >
                        {listing.title}
                      </Link>
                    </CardTitle>
                    <CardDescription>
                      {listing.sales_count}{" "}
                      {listing.sales_count === 1 ? "sale" : "sales"}
                      {Object.entries(listing.earnings_by_token).map(
                        ([token, amount]) => (
                          <span key={token}>
                            {" · "}
                            {formatAtomicAmount(amount, listing.token_decimals)}{" "}
                            {listing.token_symbol}
                          </span>
                        ),
                      )}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <p className="text-sm font-medium">
                        Price: {formatAtomicAmount(listing.price, listing.token_decimals)}{" "}
                        {listing.token_symbol}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {listing.price_editable
                          ? "Editing prices from your wallet is coming soon."
                          : "Price can't change after the first sale."}
                      </p>
                    </div>
                    {/* Price edits must be signed by the seller's wallet; the
                        client has no updatePrice helper yet, so the control
                        stays disabled. */}
                    <Button variant="outline" className="gap-2" disabled>
                      <Pencil className="h-4 w-4" />
                      Edit price
                    </Button>
                  </CardContent>
                </Card>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

export default SellerDashboard;
