import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Download, KeyRound, LoaderCircle, Wallet } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
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
import {
  downloadPurchasedDataset,
  type DownloadStep,
} from "@/lib/dataset-download";
import { formatAtomicAmount } from "@/lib/marketplace";
import { useWalletStore } from "@/stores/wallet-store";
import type { PurchasedListing } from "@/types/me";

const STEP_LABEL: Record<DownloadStep, string> = {
  authorizing: "Authorizing...",
  decrypting: "Decrypting...",
  downloading: "Downloading...",
};

function MyDatasets() {
  const isConnected = useWalletStore((state) => state.isConnected);
  const address = useWalletStore((state) => state.address);

  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<{
    key: string;
    rows?: PurchasedListing[];
    error?: string;
  } | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [step, setStep] = useState<DownloadStep | null>(null);

  // Results are tied to the wallet and attempt that requested them, so a
  // different wallet never sees the previous wallet's rows.
  const key = `${address ?? ""}:${attempt}`;
  const current = result?.key === key ? result : null;
  const items = current?.rows ?? null;
  const error = current?.error ?? null;

  const retry = () => setAttempt((n) => n + 1);

  useEffect(() => {
    if (!isConnected || !address) return;
    let cancelled = false;
    backend
      .getMyPurchases()
      .then((rows) => {
        if (!cancelled) setResult({ key, rows });
      })
      .catch((err: unknown) => {
        if (!cancelled)
          setResult({
            key,
            error: err instanceof Error ? err.message : "Failed to load datasets.",
          });
      });
    return () => {
      cancelled = true;
    };
  }, [isConnected, address, key]);


  const handleDownload = async (item: PurchasedListing) => {
    setBusyId(item.listing_id);
    setStep("authorizing");
    try {
      await downloadPurchasedDataset(item.listing_id, item.dataset_url, setStep);
      toast.success("Dataset ready", {
        description: "Key released and file downloaded successfully.",
      });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Download failed");
    } finally {
      setBusyId(null);
      setStep(null);
    }
  };

  if (!isConnected) {
    return (
      <div className="mx-auto flex min-h-[50vh] w-full max-w-2xl flex-col items-center justify-center gap-3 px-4 py-8 text-center">
        <Wallet className="h-8 w-8" />
        <h1 className="text-2xl font-bold">My datasets</h1>
        <p className="text-sm text-muted-foreground">
          Connect your wallet to see the datasets you have bought.
        </p>
        <Link to="/">
          <Button variant="outline">Back to marketplace</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-8">
      <h1 className="text-2xl font-bold">My datasets</h1>
      <p className="mt-1 mb-6 text-sm text-muted-foreground">
        Datasets you have purchased. Download them again at any time.
      </p>

      {error && (
        <ErrorPanel
          title="Could not load your datasets"
          message={error}
          onRetry={retry}
        />
      )}

      {!error && items === null && (
        <div className="space-y-3" data-testid="my-datasets-loading">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      )}

      {!error && items !== null && items.length === 0 && (
        <div className="rounded-xl border p-8 text-center">
          <p className="font-medium">You haven't bought any datasets yet.</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Browse the marketplace to find one.
          </p>
          <Link to="/">
            <Button className="mt-4">Browse datasets</Button>
          </Link>
        </div>
      )}

      {!error && items !== null && items.length > 0 && (
        <ul className="space-y-3">
          {items.map((item) => {
            const busy = busyId === item.listing_id;
            return (
              <li key={item.listing_id}>
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between gap-2">
                      <Link
                        to={`/dataset/${item.listing_id}`}
                        className="hover:underline"
                      >
                        {item.title}
                      </Link>
                      <Badge variant="secondary">
                        {formatAtomicAmount(item.price_paid, item.token_decimals)}{" "}
                        {item.token_symbol}
                      </Badge>
                    </CardTitle>
                    <CardDescription>{item.description}</CardDescription>
                  </CardHeader>
                  <CardContent className="flex items-center justify-between gap-2">
                    <span className="text-xs text-muted-foreground">
                      {item.purchased_at
                        ? `Purchased ${new Date(item.purchased_at).toLocaleDateString()}`
                        : "Purchased"}
                    </span>
                    <Button
                      variant="outline"
                      className="gap-2"
                      disabled={busyId !== null}
                      onClick={() => void handleDownload(item)}
                    >
                      {busy ? (
                        <>
                          <LoaderCircle className="h-4 w-4 animate-spin" />
                          {step ? STEP_LABEL[step] : "Working..."}
                        </>
                      ) : (
                        <>
                          <KeyRound className="h-4 w-4" />
                          <Download className="h-4 w-4" />
                          Download
                        </>
                      )}
                    </Button>
                  </CardContent>
                </Card>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

export default MyDatasets;
