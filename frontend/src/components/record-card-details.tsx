import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  CheckCircle2,
  Download,
  Copy,
  FileText,
  CalendarDays,
  User,
  Shield,
  Layers,
} from "lucide-react";
import { toast } from "sonner";
import type { DatasetRecord } from "@/types/dataset";

interface RecordCardDetailsProps {
  dataset: DatasetRecord;
  isPurchased?: boolean;
}

function RecordCardDetails({
  dataset,
  isPurchased = false,
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

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-start justify-between mb-2">
          <h1 className="text-3xl font-bold">{dataset.title}</h1>
          {dataset.verified && (
            <Badge variant="default" className="gap-1">
              <CheckCircle2 className="h-3 w-3" />
              Verified
            </Badge>
          )}
        </div>
        <p className="text-muted-foreground">{dataset.description}</p>
        <div className="flex flex-wrap gap-2 mt-4">
          {dataset.tags.map((tag) => (
            <Badge key={tag} variant="outline">
              {tag}
            </Badge>
          ))}
        </div>
      </div>

      {/* Price & Actions */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Price</p>
              <p className="text-3xl font-bold font-mono">
                {dataset.priceEth} ETH
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                {dataset.downloads} downloads
              </p>
            </div>
            {!isPurchased && (
              <Button size="lg" className="gap-2">
                <Download className="h-4 w-4" />
                Purchase & Download
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Metadata Summary */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Metadata Summary
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Rows</p>
              <p className="text-lg font-semibold">
                {dataset.rows.toLocaleString()}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Columns</p>
              <p className="text-lg font-semibold">{dataset.columns}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">File Size</p>
              <p className="text-lg font-semibold">{dataset.fileSizeMB} MB</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Format</p>
              <p className="text-lg font-semibold uppercase">
                {dataset.format}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Domain</p>
              <p className="text-lg font-semibold">{dataset.domain}</p>
            </div>
            {dataset.target && (
              <div>
                <p className="text-sm text-muted-foreground">Target Type</p>
                <p className="text-lg font-semibold capitalize">
                  {dataset.target.type}
                </p>
              </div>
            )}
          </div>
          {dataset.target && (
            <>
              <Separator />
              <div>
                <p className="text-sm text-muted-foreground">Target Variable</p>
                <p className="font-mono text-sm bg-muted px-2 py-1 rounded mt-1">
                  {dataset.target.name}
                </p>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Vector Spec Panel */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Layers className="h-5 w-5" />
            Vector Specification
          </CardTitle>
          <CardDescription>
            Embedding model and vector configuration
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Embedding Model</p>
              <p className="font-mono text-sm font-semibold">
                {dataset.vectorSpec.embeddingModel}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Dimension</p>
              <p className="text-lg font-semibold">
                {dataset.vectorSpec.dimension}d
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Distance Metric</p>
              <p className="text-lg font-semibold capitalize">
                {dataset.vectorSpec.distanceMetric}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Normalized</p>
              <p className="text-lg font-semibold">
                {dataset.vectorSpec.normalized ? "Yes" : "No"}
              </p>
            </div>
          </div>
          <Separator />
          <div>
            <p className="text-sm text-muted-foreground">Template Version</p>
            <Badge variant="secondary" className="mt-1 font-mono">
              {dataset.vectorSpec.templateVersion}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Seller & Created Date */}
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
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <CalendarDays className="h-4 w-4" />
            <span>Listed on {formatDate(dataset.createdAt)}</span>
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
            <p className="text-sm text-muted-foreground mb-2">
              Access Data Hash
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 bg-muted px-3 py-2 rounded font-mono text-xs break-all">
                {dataset.accessSha256}
              </code>
              <Button
                variant="outline"
                size="icon"
                onClick={() =>
                  copyToClipboard(dataset.accessSha256, "Access hash")
                }
              >
                <Copy className="h-4 w-4" />
              </Button>
            </div>
          </div>
          <div>
            <p className="text-sm text-muted-foreground mb-2">
              Vector Data Hash
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 bg-muted px-3 py-2 rounded font-mono text-xs break-all">
                {dataset.vectorSha256}
              </code>
              <Button
                variant="outline"
                size="icon"
                onClick={() =>
                  copyToClipboard(dataset.vectorSha256, "Vector hash")
                }
              >
                <Copy className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Download Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Download Data</CardTitle>
          <CardDescription>
            {isPurchased
              ? "Your purchased datasets are available for download"
              : "Purchase this dataset to unlock downloads"}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Button
            variant="outline"
            className="w-full gap-2"
            disabled={!isPurchased}
          >
            <Download className="h-4 w-4" />
            Download CSV ({dataset.fileSizeMB} MB)
          </Button>
          <Button
            variant="outline"
            className="w-full gap-2"
            disabled={!isPurchased}
          >
            <Download className="h-4 w-4" />
            Download Vectors
          </Button>
          <Button
            variant="outline"
            className="w-full gap-2"
            disabled={!isPurchased}
          >
            <Download className="h-4 w-4" />
            Download Metadata
          </Button>
          {!isPurchased && (
            <p className="text-xs text-center text-muted-foreground mt-2">
              Downloads will be enabled after purchase
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default RecordCardDetails;
