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
  Hexagon,
  Orbit,
  Coins,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import { toast } from "sonner";
import type { MarketplaceDataItem } from "@/types/contract";
import { Badge } from "@/components/ui/badge";
import { weiToEth } from "@/lib/marketplace";
import { useCurrency } from "@/context/currency-context";
import { convertEthToCurrency, formatCurrencyAmount } from "@/lib/fx";

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
    } catch (error) {
      toast.error("Failed to copy to clipboard");
    }
  };

  const priceEth = weiToEth(dataset.price);
  const { preferredCurrency, rates } = useCurrency();
  const equivalent =
    preferredCurrency !== "ETH"
      ? convertEthToCurrency(Number(priceEth), preferredCurrency, rates)
      : null;
  const sellerIsEvm = /^0x[a-fA-F0-9]{40}$/.test(dataset.seller);
  const sellerIsSolana = /^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(dataset.seller);

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

      {/* Price & Actions */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Price</p>
              <p className="text-3xl font-bold font-mono">
                <span className="inline-flex items-center gap-1">
                  <Coins className="h-6 w-6" />
                  {priceEth} ETH
                </span>
              </p>
              {equivalent !== null && (
                <p className="mt-1 text-sm text-muted-foreground">
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
              <p className="text-sm text-muted-foreground">Price (wei)</p>
              <p className="font-mono text-xs break-all">{dataset.price}</p>
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
              <p className="flex-1 font-mono text-xs break-all">{dataset.dataset_url}</p>
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
              <Badge variant="outline">
                {sellerIsEvm ? (
                  <>
                    <Hexagon className="mr-1 h-3.5 w-3.5" />
                    Ethereum
                  </>
                ) : sellerIsSolana ? (
                  <>
                    <Orbit className="mr-1 h-3.5 w-3.5" />
                    Solana
                  </>
                ) : (
                  "Unknown Chain"
                )}
              </Badge>
            </div>
            <div className="flex items-center gap-2">
              <code className="flex-1 bg-muted px-3 py-2 rounded font-mono text-sm">
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
