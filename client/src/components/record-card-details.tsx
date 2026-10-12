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
  User,
  Shield,
  Users,
  CheckCircle2,
  AlertCircle,
  TableIcon,
} from "lucide-react";
import { toast } from "sonner";
import type { MarketplaceDataItem } from "@/types/contract";
import { Badge } from "@/components/ui/badge";
import { ChainIcon, detectAddressChain } from "@/components/chain-icon";
import { convertSettlementToCurrency, formatCurrencyAmount } from "@/lib/fx";
import { normalizeMarketplacePrice } from "@/lib/marketplace";
import { useCurrencyStore } from "@/stores/currency-store";

interface RecordCardDetailsProps {
  dataset: MarketplaceDataItem;
  isPurchased?: boolean;
  integrityStatus?: "verifying" | "verified" | "failed" | "unavailable";
  integrityDetail?: string;
  preview?: { column_names: string[]; rows: string[][] } | null;
}

function RecordCardDetails({
  dataset,
  isPurchased = false,
  integrityStatus = "unavailable",
  integrityDetail,
  preview,
}: RecordCardDetailsProps) {
  const copyToClipboard = async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text);
      toast(`${label} copied to clipboard`, { description: text });
    } catch {
      toast.error("Failed to copy to clipboard");
    }
  };

  const pricing = normalizeMarketplacePrice(dataset);
  const logoSrc =
    pricing.settlementCurrency === "CADC" ? "/cadc-logo.svg" : "/usdc-logo.svg";
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
          pricing.settlementCurrency,
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
          <p className="mt-2 text-xs text-muted-foreground">{integrityDetail}</p>
        )}
      </div>

      {/* Price */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Price</p>
              <p className="mt-1 inline-flex items-center gap-2 text-3xl font-bold font-mono">
                <img
                  src={logoSrc}
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
              {isPurchased ? "Access granted" : "Purchase to unlock full dataset"}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Dataset Preview */}
      {preview ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TableIcon className="h-5 w-5" />
              Dataset Preview
            </CardTitle>
            <CardDescription>
              First {preview.rows.length} row{preview.rows.length !== 1 ? "s" : ""} ·{" "}
              {preview.column_names.length} column{preview.column_names.length !== 1 ? "s" : ""}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto rounded-md border">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b bg-muted/50">
                    {preview.column_names.map((col) => (
                      <th
                        key={col}
                        className="px-3 py-2 text-left font-semibold text-muted-foreground whitespace-nowrap"
                      >
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {preview.rows.map((row, ri) => (
                    <tr
                      key={ri}
                      className="border-b last:border-0 hover:bg-muted/30 transition-colors"
                    >
                      {row.map((cell, ci) => (
                        <td key={ci} className="px-3 py-2 font-mono whitespace-nowrap">
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card className="border-dashed">
          <CardContent className="flex items-center gap-3 py-5 text-sm text-muted-foreground">
            <TableIcon className="h-5 w-5 shrink-0 opacity-50" />
            <span>Dataset preview is not available for this listing yet.</span>
          </CardContent>
        </Card>
      )}

      {/* Seller */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="h-5 w-5" />
            Seller
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="mb-1">
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
              onClick={() => copyToClipboard(dataset.seller, "Seller address")}
            >
              <Copy className="h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Integrity */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Integrity
          </CardTitle>
          <CardDescription>SHA-256 hash of the encrypted dataset</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2">
            <code className="flex-1 bg-muted px-3 py-2 rounded font-mono text-xs break-all">
              {dataset.dataset_hash}
            </code>
            <Button
              variant="outline"
              size="icon"
              onClick={() => copyToClipboard(dataset.dataset_hash, "Dataset hash")}
            >
              <Copy className="h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default RecordCardDetails;
