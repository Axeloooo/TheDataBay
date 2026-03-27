import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Copy,
  FileText,
  User,
  Shield,
  Link2,
  Users,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import { toast } from "sonner";
import type { MarketplaceDataItem } from "@/types/contract";
import { Badge } from "@/components/ui/badge";
import { ChainIcon, detectAddressChain } from "@/components/chain-icon";
import {
  convertSettlementToCurrency,
  formatCurrencyAmount,
} from "@/lib/fx";
import { normalizeMarketplacePrice } from "@/lib/marketplace";
import { useCurrencyStore } from "@/stores/currency-store";

interface RecordCardDetailsProps {
  dataset: MarketplaceDataItem;
  isPurchased?: boolean;
  integrityStatus?: "verifying" | "verified" | "failed" | "unavailable";
  integrityDetail?: string;
}

function RecordCardDetails({
  dataset,
  isPurchased = false,
  integrityStatus = "unavailable",
  integrityDetail,
}: RecordCardDetailsProps) {
  const copyToClipboard = async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text);
      toast(`${label} copied to clipboard`, {
        description: text,
      });
    } catch {
      toast.error("Failed to copy to clipboard");
    }
  };

  const pricing = normalizeMarketplacePrice(dataset);
  const preferredCurrency = useCurrencyStore(
    (state) => state.preferredCurrency,
  );
  const rates = useCurrencyStore((state) => state.rates);
  const equivalent =
    preferredCurrency !== pricing.settlementCurrency
      ? convertSettlementToCurrency(
          Number(pricing.settlementAmount),
          preferredCurrency,
          rates,
        )
      : null;
  const sellerChain = detectAddressChain(dataset.seller);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-start justify-between mb-2">
          <h1 className="text-3xl font-bold">{dataset.title}</h1>
          <div className="flex items-center gap-2">
            <Badge
              variant="outline"
              className={
                isPurchased
                  ? "border-emerald-300 bg-emerald-50 text-emerald-700"
                  : "border-amber-300 bg-amber-50 text-amber-700"
              }
            >
              {isPurchased ? "Access Granted" : "No Access"}
            </Badge>
            <Badge
              variant="outline"
              className={
                integrityStatus === "verified"
                  ? "border-emerald-300 bg-emerald-50 text-emerald-700"
                  : integrityStatus === "failed"
                    ? "border-red-300 bg-red-50 text-red-700"
                    : "border-slate-300 bg-slate-50 text-slate-700"
              }
            >
              {integrityStatus === "verified" ? (
                <>
                  <CheckCircle2 className="mr-1 h-3.5 w-3.5" />
                  Verified
                </>
              ) : integrityStatus === "failed" ? (
                <>
                  <AlertCircle className="mr-1 h-3.5 w-3.5" />
                  Verification Failed
                </>
              ) : integrityStatus === "verifying" ? (
                "Verifying..."
              ) : (
                "Not Verified"
              )}
            </Badge>
          </div>
        </div>
        <p className="text-muted-foreground">{dataset.description}</p>
        {integrityDetail && integrityStatus !== "verified" && (
          <p className="mt-2 text-xs text-muted-foreground">
            {integrityDetail}
          </p>
        )}
      </div>

      {/* Price & Actions */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Price</p>
              <p className="mt-1 inline-flex items-center gap-2 text-3xl font-bold font-mono">
                <img
                  src="/usdc-logo.svg"
                  alt=""
                  aria-hidden="true"
                  className="h-7 w-7 rounded-full object-contain"
                />
                <span>{pricing.settlementAmount}</span>
                <span className="text-xl font-semibold text-muted-foreground">
                  {pricing.settlementCurrency}
                </span>
              </p>
              {equivalent !== null && (
                <p className="mt-2 text-sm text-muted-foreground">
                  ~ {formatCurrencyAmount(equivalent, preferredCurrency)}
                </p>
              )}
              <div className="flex items-center gap-2 text-sm text-muted-foreground mt-1">
                <Users className="h-4 w-4" />
                <span>{dataset.purchase_count} purchases</span>
              </div>
            </div>
            <div className="text-sm text-muted-foreground">
              {isPurchased ? "Access granted" : "Purchase to unlock"}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Listing Summary */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Listing Summary
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Listing ID</p>
              <p className="font-mono text-xs break-all">{dataset.id}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Price atomic</p>
              <p className="font-mono text-xs break-all">{pricing.priceAtomic}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                {pricing.settlementCurrency} settlement at{" "}
                {pricing.settlementDecimals} decimals
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* URLs */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Link2 className="h-5 w-5" />
            URLs
          </CardTitle>
          <CardDescription>
            Encrypted dataset and signature locations
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p className="text-sm text-muted-foreground">Dataset URL</p>
            <div className="flex items-center gap-2">
              <p className="flex-1 font-mono text-xs break-all">
                {dataset.dataset_url}
              </p>
              <Button
                variant="outline"
                size="icon"
                onClick={() =>
                  copyToClipboard(dataset.dataset_url, "Dataset URL")
                }
              >
                <Copy className="h-4 w-4" />
              </Button>
            </div>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Signature URL</p>
            <div className="flex items-center gap-2">
              <p className="flex-1 font-mono text-xs break-all">
                {dataset.signature_url}
              </p>
              <Button
                variant="outline"
                size="icon"
                onClick={() =>
                  copyToClipboard(dataset.signature_url, "Signature URL")
                }
              >
                <Copy className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Seller */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="h-5 w-5" />
            Seller Information
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p className="text-sm text-muted-foreground mb-2">Seller Address</p>
            <div className="mb-2">
              <Badge variant="outline" className="gap-1.5">
                {sellerChain === "evm" ? (
                  <>
                    <ChainIcon chain="evm" className="h-3.5 w-3.5" />
                    Ethereum
                  </>
                ) : sellerChain === "solana" ? (
                  <>
                    <ChainIcon chain="solana" className="h-3.5 w-3.5" />
                    Solana
                  </>
                ) : (
                  "Unknown Chain"
                )}
              </Badge>
            </div>
            <div className="flex items-center gap-2">
              {sellerChain && (
                <div className="flex h-10 w-10 items-center justify-center rounded-md border bg-muted/60">
                  <ChainIcon chain={sellerChain} className="h-5 w-5" />
                </div>
              )}
              <code className="flex-1 rounded bg-muted px-3 py-2 font-mono text-sm">
                {dataset.seller}
              </code>
              <Button
                variant="outline"
                size="icon"
                onClick={() =>
                  copyToClipboard(dataset.seller, "Seller address")
                }
              >
                <Copy className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Integrity Hashes */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Integrity Hashes
          </CardTitle>
          <CardDescription>
            SHA-256 hashes for data verification
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p className="text-sm text-muted-foreground mb-2">Dataset Hash</p>
            <div className="flex items-center gap-2">
              <code className="flex-1 bg-muted px-3 py-2 rounded font-mono text-xs break-all">
                {dataset.dataset_hash}
              </code>
              <Button
                variant="outline"
                size="icon"
                onClick={() =>
                  copyToClipboard(dataset.dataset_hash, "Dataset hash")
                }
              >
                <Copy className="h-4 w-4" />
              </Button>
            </div>
          </div>
          <div>
            <p className="text-sm text-muted-foreground mb-2">Signature Hash</p>
            <div className="flex items-center gap-2">
              <code className="flex-1 bg-muted px-3 py-2 rounded font-mono text-xs break-all">
                {dataset.signature_hash}
              </code>
              <Button
                variant="outline"
                size="icon"
                onClick={() =>
                  copyToClipboard(dataset.signature_hash, "Signature hash")
                }
              >
                <Copy className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default RecordCardDetails;
