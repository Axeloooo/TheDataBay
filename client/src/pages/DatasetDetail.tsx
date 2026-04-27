import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  ArrowLeft,
  Download,
  KeyRound,
  ShoppingCart,
  LoaderCircle,
} from "lucide-react";
import RecordCardDetails from "@/components/record-card-details";
import { DisplayCurrencySelector } from "@/components/display-currency-selector";
import { backend } from "@/lib/backend";
import type { MarketplaceDataItem } from "@/types/contract";
import {
  buyItemTx,
  isSameAddress,
  normalizeMarketplacePrice,
} from "@/lib/marketplace";
import { bytes32ToUuid } from "@/lib/ids";
import { decodeBase64, decryptAesGcm, utf8Bytes } from "@/lib/crypto";
import { resolveIpfsUrl } from "@/lib/ipfs";
import ErrorPanel from "@/components/ui/error-panel";
import { Skeleton } from "@/components/ui/skeleton";
import { DatasetRecommendations } from "@/components/dataset-recommendations";
import { toast } from "sonner";
import { fireConfettiBurst } from "@/lib/confetti";
import { verifyDatasetIntegrity, type IntegrityStatus } from "@/lib/integrity";
import { convertSettlementToCurrency, formatCurrencyAmount } from "@/lib/fx";
import { useWalletStore } from "@/stores/wallet-store";
import { useCurrencyStore } from "@/stores/currency-store";

function mapDatasetError(raw: string | null, hasListingUuid: boolean) {
  if (!hasListingUuid) {
    return {
      title: "Invalid dataset link",
      message:
        "The dataset identifier in the URL is invalid. Please open the listing from the marketplace page.",
    };
  }
  if (!raw) {
    return {
      title: "Unable to load dataset",
      message: "The dataset could not be loaded right now. Please try again.",
    };
  }
  const normalized = raw.toLowerCase();
  if (
    normalized.includes("item does not exist") ||
    normalized.includes("not found")
  ) {
    return {
      title: "Dataset not found",
      message:
        "This listing does not exist on-chain yet. It may still be pending creation.",
    };
  }
  if (normalized.includes("rpc") || normalized.includes("network")) {
    return {
      title: "Network connection problem",
      message:
        "We could not reach the blockchain RPC node. Check your local chain and try again.",
    };
  }
  return {
    title: "Unable to load dataset",
    message: raw,
  };
}

function mapActionError(raw: string | null) {
  if (!raw) return "";
  const normalized = raw.toLowerCase();
  if (normalized.includes("no contract code found")) {
    return (
      "No deployed Marketplace contract was found on your current wallet network. " +
      "Switch MetaMask network or update VITE_CONTRACT_ADDRESS."
    );
  }
  if (normalized.includes("seller cannot buy")) {
    return "You cannot purchase your own listing from the seller account.";
  }
  if (normalized.includes("connect wallet")) {
    return "Connect your wallet before running this action.";
  }
  if (normalized.includes("access not authorized")) {
    return "You do not have access to release the key for this dataset.";
  }
  if (normalized.includes("decrypt")) {
    return "Failed to decrypt dataset payload. The key or nonce may be invalid.";
  }
  return raw;
}

function DatasetDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const address = useWalletStore((state) => state.address);
  const rates = useCurrencyStore((state) => state.rates);
  const preferredCurrency = useCurrencyStore(
    (state) => state.preferredCurrency,
  );

  const [dataset, setDataset] = useState<MarketplaceDataItem | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionError, setActionError] = useState<string | null>(null);
  const [isBuying, setIsBuying] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [isPurchased, setIsPurchased] = useState(false);
  const [quoteCurrency, setQuoteCurrency] = useState(preferredCurrency);
  const [downloadStep, setDownloadStep] = useState<
    "idle" | "authorizing" | "decrypting" | "downloading"
  >("idle");
  const [integrityStatus, setIntegrityStatus] =
    useState<IntegrityStatus>("verifying");
  const [integrityDetail, setIntegrityDetail] = useState<string | undefined>(
    undefined,
  );

  const listingUuid = useMemo(() => {
    if (!id) return null;
    try {
      return bytes32ToUuid(id);
    } catch {
      return null;
    }
  }, [id]);

  useEffect(() => {
    if (!id) return;
    if (!listingUuid) {
      setError("Invalid listing identifier.");
      setLoading(false);
    }
  }, [id, listingUuid]);

  useEffect(() => {
    if (!listingUuid) return;
    let active = true;
    backend
      .getMarketplaceItem(listingUuid)
      .then((data) => {
        if (!active) return;
        setDataset(data);
        setError(null);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Failed to load dataset");
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [listingUuid]);

  useEffect(() => {
    if (!dataset) return;
    let active = true;
    setIntegrityStatus("verifying");
    setIntegrityDetail(undefined);
    verifyDatasetIntegrity({
      datasetUrl: dataset.dataset_url,
      datasetHash: dataset.dataset_hash,
    }).then((result) => {
      if (!active) return;
      setIntegrityStatus(result.status);
      setIntegrityDetail(result.detail);
    });
    return () => {
      active = false;
    };
  }, [dataset]);

  useEffect(() => {
    if (!listingUuid || !address) {
      setIsPurchased(false);
      return;
    }
    let active = true;
    backend
      .checkAccess(listingUuid, { wallet_type: "evm", address })
      .then((res) => {
        if (!active) return;
        setIsPurchased(res.has_access);
      })
      .catch(() => {
        if (!active) return;
        setIsPurchased(false);
      });
    return () => {
      active = false;
    };
  }, [listingUuid, address]);

  useEffect(() => {
    setQuoteCurrency(preferredCurrency);
  }, [preferredCurrency]);

  const pricing = useMemo(
    () => (dataset ? normalizeMarketplacePrice(dataset) : null),
    [dataset],
  );
  const settlementLogo =
    pricing?.settlementCurrency === "CADC"
      ? "/cadc-logo.svg"
      : "/usdc-logo.svg";
  const canBuy = dataset ? !isSameAddress(dataset.seller, address) : false;
  const quoteEquivalent =
    pricing && quoteCurrency !== pricing.settlementCurrency
      ? convertSettlementToCurrency(
          Number(pricing.settlementAmount),
          quoteCurrency,
          rates,
          pricing.settlementCurrency,
        )
      : null;

  if (loading) {
    return (
      <div className="min-h-screen">
        <div className="mx-auto w-full max-w-4xl px-4 py-6 space-y-4">
          <Skeleton className="h-10 w-44" />
          <div className="rounded-xl border p-6 space-y-4">
            <Skeleton className="h-8 w-2/3" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
            <Skeleton className="h-24 w-full" />
          </div>
          <div className="rounded-xl border p-6 space-y-3">
            <Skeleton className="h-5 w-1/3" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-4/5" />
          </div>
        </div>
      </div>
    );
  }

  if (!dataset || error) {
    const friendly = mapDatasetError(error, !!listingUuid);
    return (
      <div className="min-h-screen">
        <div className="mx-auto w-full max-w-4xl px-4 py-6 space-y-4">
          <Button
            variant="ghost"
            onClick={() => navigate("/")}
            className="gap-2"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Marketplace
          </Button>
          <ErrorPanel
            title={friendly.title}
            message={friendly.message}
            onRetry={listingUuid ? () => window.location.reload() : undefined}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <div className="mx-auto w-full max-w-4xl px-4 py-6">
        <Button
          variant="ghost"
          onClick={() => navigate("/")}
          className="mb-4 gap-2"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Marketplace
        </Button>
        <RecordCardDetails
          dataset={dataset}
          isPurchased={isPurchased}
          integrityStatus={integrityStatus}
          integrityDetail={integrityDetail}
        />
        {listingUuid && <DatasetRecommendations listingId={listingUuid} />}
        {actionError && (
          <div className="mt-4">
            <ErrorPanel
              title="Action failed"
              message={mapActionError(actionError)}
            />
          </div>
        )}
        <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-end">
          <div className="rounded-lg border border-border/75 bg-card/55 px-3 py-3 text-xs text-muted-foreground shadow-sm">
            <p className="mb-2 font-medium text-foreground">Quote currency</p>
            <DisplayCurrencySelector
              value={quoteCurrency}
              onChange={setQuoteCurrency}
              compact
              title="Quote currency"
              buttonClassName="h-8"
            />
            <p className="mt-2 max-w-xs">
              Quotes only. Settlement uses the listing's token at{" "}
              {pricing?.settlementDecimals ?? 6} decimals.
            </p>
          </div>
          {!isPurchased && (
            <Button
              className="gap-2"
              onClick={async () => {
                if (!id) return;
                if (!address) {
                  setActionError("Connect wallet to purchase.");
                  return;
                }
                if (!canBuy) {
                  setActionError("Seller cannot buy their own listing.");
                  return;
                }
                if (
                  !pricing?.priceAtomic ||
                  !/^\d+$/.test(pricing.priceAtomic)
                ) {
                  setActionError(
                    "Price unavailable. Please refresh and try again.",
                  );
                  return;
                }
                setActionError(null);
                setIsBuying(true);
                try {
                  const priceAtomic = BigInt(pricing.priceAtomic);
                  await buyItemTx(id, priceAtomic, dataset.payment_token);
                  setIsPurchased(true);
                  toast.success("Purchase successful", {
                    description: "Access granted for this dataset.",
                  });
                  fireConfettiBurst();
                } catch (err) {
                  setActionError(
                    err instanceof Error ? err.message : "Purchase failed",
                  );
                } finally {
                  setIsBuying(false);
                }
              }}
              disabled={isBuying}
            >
              {isBuying ? (
                <>
                  <LoaderCircle className="h-4 w-4 animate-spin" />
                  Purchasing...
                </>
              ) : (
                <>
                  <img
                    src={settlementLogo}
                    alt=""
                    aria-hidden="true"
                    className="h-4 w-4 rounded-full object-contain"
                  />
                  <ShoppingCart className="h-4 w-4" />
                  Buy with {pricing?.settlementCurrency ?? "USDC"} ({pricing?.settlementAmount ?? "0"} {pricing?.settlementCurrency ?? "USDC"}
                  {quoteEquivalent !== null
                    ? ` • ~${formatCurrencyAmount(quoteEquivalent, quoteCurrency)}`
                    : ""}
                  )
                </>
              )}
            </Button>
          )}
          <Button
            variant="outline"
            className="gap-2"
            onClick={async () => {
              if (!listingUuid) {
                setActionError("Invalid listing id format.");
                return;
              }
              if (!address) {
                setActionError("Connect wallet to download.");
                return;
              }
              setActionError(null);
              setIsDownloading(true);
              setDownloadStep("authorizing");
              try {
                const keyResponse = await backend.requestKeyRelease(
                  listingUuid,
                  {
                    wallet_type: "evm",
                    address,
                  },
                );
                setDownloadStep("decrypting");
                const datasetUrl = resolveIpfsUrl(dataset.dataset_url);
                const res = await fetch(datasetUrl);
                if (!res.ok) {
                  throw new Error(`Failed to download dataset (${res.status})`);
                }
                const ciphertext = await res.arrayBuffer();
                const keyBytes = decodeBase64(keyResponse.key_b64);
                const nonceBytes = decodeBase64(keyResponse.nonce_b64);
                const aad = utf8Bytes(listingUuid);
                const plaintext = await decryptAesGcm({
                  ciphertext,
                  key: keyBytes,
                  nonce: nonceBytes,
                  aad,
                });
                setDownloadStep("downloading");
                const blob = new Blob([plaintext], { type: "text/csv" });
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `${listingUuid}.csv`;
                document.body.appendChild(a);
                a.click();
                a.remove();
                URL.revokeObjectURL(url);
                setIsPurchased(true);
                toast.success("Dataset ready", {
                  description: "Key released and file downloaded successfully.",
                });
                fireConfettiBurst();
              } catch (err) {
                setActionError(
                  err instanceof Error ? err.message : "Download failed",
                );
              } finally {
                setIsDownloading(false);
                setDownloadStep("idle");
              }
            }}
            disabled={isDownloading}
          >
            {isDownloading ? (
              <>
                <LoaderCircle className="h-4 w-4 animate-spin" />
                {downloadStep === "authorizing"
                  ? "Authorizing..."
                  : downloadStep === "downloading"
                    ? "Downloading..."
                    : "Decrypting..."}
              </>
            ) : (
              <>
                <KeyRound className="h-4 w-4" />
                <Download className="h-4 w-4" />
                Release Key & Download
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

export default DatasetDetail;
