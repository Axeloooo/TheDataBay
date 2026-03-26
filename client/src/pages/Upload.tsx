import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Upload as UploadIcon,
  FileUp,
  Copy,
  AlertTriangle,
  LoaderCircle,
  BadgeCheck,
  PenLine,
  Wallet,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useEffect, useMemo, useRef } from "react";
import { uuidToBytes32 } from "@/lib/ids";
import { toast } from "sonner";
import ErrorPanel from "@/components/ui/error-panel";
import { DisplayCurrencySelector } from "@/components/display-currency-selector";
import {
  convertSettlementToCurrency,
  formatCurrencyAmount,
} from "@/lib/fx";
import { isSameAddress } from "@/lib/marketplace";
import { useCurrencyStore } from "@/stores/currency-store";
import { useWalletStore } from "@/stores/wallet-store";
import { selectUploadPriceAtomic, useUploadStore } from "@/stores/upload-store";
import { ChainIcon } from "@/components/chain-icon";

function Upload() {
  const isConnected = useWalletStore((state) => state.isConnected);
  const address = useWalletStore((state) => state.address);
  const connect = useWalletStore((state) => state.connect);
  const preferredCurrency = useCurrencyStore(
    (state) => state.preferredCurrency,
  );
  const rates = useCurrencyStore((state) => state.rates);
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const title = useUploadStore((state) => state.title);
  const description = useUploadStore((state) => state.description);
  const priceUsdc = useUploadStore((state) => state.priceUsdc);
  const displayCurrency = useUploadStore((state) => state.displayCurrency);
  const file = useUploadStore((state) => state.file);
  const job = useUploadStore((state) => state.job);
  const jobStatus = useUploadStore((state) => state.jobStatus);
  const loading = useUploadStore((state) => state.loading);
  const error = useUploadStore((state) => state.error);
  const createTxHash = useUploadStore((state) => state.createTxHash);
  const isCreating = useUploadStore((state) => state.isCreating);
  const persistedSession = useUploadStore((state) => state.persistedSession);

  const setTitle = useUploadStore((state) => state.setTitle);
  const setDescription = useUploadStore((state) => state.setDescription);
  const setPriceUsdc = useUploadStore((state) => state.setPriceUsdc);
  const setDisplayCurrency = useUploadStore((state) => state.setDisplayCurrency);
  const setFile = useUploadStore((state) => state.setFile);
  const setError = useUploadStore((state) => state.setError);
  const initializeUploadState = useUploadStore(
    (state) => state.initializeUploadState,
  );
  const submitUpload = useUploadStore((state) => state.submitUpload);
  const startPolling = useUploadStore((state) => state.startPolling);
  const stopPolling = useUploadStore((state) => state.stopPolling);
  const clearPendingSession = useUploadStore(
    (state) => state.clearPendingSession,
  );
  const createItemOnChain = useUploadStore((state) => state.createItemOnChain);

  const hasSubmitted = !!job || !!persistedSession;

  useEffect(() => {
    initializeUploadState(preferredCurrency);
  }, [initializeUploadState, preferredCurrency]);

  useEffect(() => {
    const activeJobId = job?.job_id ?? persistedSession?.jobId;
    const activeStatus = jobStatus?.status ?? persistedSession?.status;

    if (!activeJobId) return;
    if (activeStatus === "completed" || activeStatus === "failed") return;

    startPolling();

    return () => {
      stopPolling();
    };
  }, [
    job?.job_id,
    jobStatus?.status,
    persistedSession?.jobId,
    persistedSession?.status,
    startPolling,
    stopPolling,
  ]);

  const computedStatus = useMemo(() => {
    if (loading) return "running";
    return jobStatus?.status ?? persistedSession?.status ?? "queued";
  }, [loading, jobStatus?.status, persistedSession?.status]);

  const statusMeta = useMemo(() => {
    if (computedStatus === "completed") {
      return {
        label: "Completed",
        dotClass: "bg-emerald-500",
        badgeClass: "border-emerald-200 text-emerald-700 bg-emerald-50",
      };
    }
    if (computedStatus === "failed") {
      return {
        label: "Failed",
        dotClass: "bg-red-500",
        badgeClass: "border-red-200 text-red-700 bg-red-50",
      };
    }
    if (computedStatus === "running") {
      return {
        label: "Running",
        dotClass: "bg-amber-500",
        badgeClass: "border-amber-200 text-amber-700 bg-amber-50",
      };
    }
    return {
      label: "Queued",
      dotClass: "bg-amber-400",
      badgeClass: "border-amber-200 text-amber-700 bg-amber-50",
    };
  }, [computedStatus]);

  const priceAtomic = useMemo(
    () => selectUploadPriceAtomic(priceUsdc),
    [priceUsdc],
  );

  const priceEquivalent = useMemo(() => {
    if (!priceUsdc || displayCurrency === "USDC") return null;
    const usdcValue = Number(priceUsdc);
    if (!Number.isFinite(usdcValue)) return null;
    return convertSettlementToCurrency(usdcValue, displayCurrency, rates);
  }, [displayCurrency, priceUsdc, rates]);

  const currentListingId =
    jobStatus?.listing_id ?? persistedSession?.listingId ?? null;
  const currentDatasetUrl =
    jobStatus?.dataset_url ?? persistedSession?.datasetUrl;
  const currentDatasetHash =
    jobStatus?.dataset_hash ?? persistedSession?.datasetHash;
  const currentSignatureUrl =
    jobStatus?.signature?.signature_url ?? persistedSession?.signatureUrl;
  const currentSignatureHash =
    jobStatus?.signature?.signature_hash ?? persistedSession?.signatureHash;
  const effectiveStatus = jobStatus?.status ?? persistedSession?.status;

  const walletMismatch =
    !!address &&
    !!persistedSession?.seller &&
    !isSameAddress(persistedSession.seller, address);

  const copyToClipboard = async (value: string, label: string) => {
    try {
      await navigator.clipboard.writeText(value);
      toast(`${label} copied`, { description: value });
    } catch {
      toast.error("Failed to copy to clipboard");
    }
  };

  const formatDuration = (startMs: number, endMs: number) => {
    const totalSeconds = Math.max(0, Math.floor((endMs - startMs) / 1000));
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    if (minutes > 0) return `${minutes}m ${seconds}s`;
    return `${seconds}s`;
  };

  if (!isConnected) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center px-4 py-8">
        <div className="w-full max-w-2xl rounded-2xl border bg-card p-8 shadow-sm">
          <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl border bg-muted">
            <Wallet className="h-6 w-6" />
          </div>
          <h1 className="text-2xl font-bold">
            Connect Wallet to List Datasets
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Listing requires an EVM wallet signature. Connect your wallet to
            upload, encrypt, and publish USDC-settled datasets on-chain.
          </p>
          <p className="mt-2 text-xs text-muted-foreground">
            Solana wallet connection is planned for upcoming cross-chain
            support.
          </p>
          <div className="mt-6 flex flex-col gap-3 sm:flex-row">
            <Button className="gap-2" onClick={() => void connect()}>
              <ChainIcon chain="evm" className="h-4 w-4" />
              Connect Ethereum Wallet
            </Button>
            <Button variant="outline" onClick={() => navigate("/")}>
              Back to Marketplace
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <div className="mx-auto w-full max-w-4xl px-4 py-12">
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">Sell Your Dataset</h1>
          <p className="text-muted-foreground">
            List your dataset with embeddings on the marketplace and settle
            sales in USDC.
          </p>
        </div>

        {persistedSession && !jobStatus && (
          <div className="mb-4 flex items-center justify-between rounded-lg border bg-amber-50 p-3 text-sm text-amber-900">
            <span>
              Resumed pending upload session for listing{" "}
              {persistedSession.listingId ?? "pending"}.
            </span>
            <Button variant="outline" size="sm" onClick={clearPendingSession}>
              Discard Session
            </Button>
          </div>
        )}

        <form
          className="space-y-6"
          onSubmit={async (event) => {
            event.preventDefault();
            await submitUpload(address);
          }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Basic Information</CardTitle>
              <CardDescription>
                Provide details about your dataset
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="title">Dataset Title</Label>
                <Input
                  id="title"
                  placeholder="e.g., UCI Heart Disease Dataset"
                  required
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  placeholder="Describe your dataset, its features, and potential use cases..."
                  rows={4}
                  required
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                />
              </div>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="price">Price (USDC)</Label>
                  <Input
                    id="price"
                    type="number"
                    step="0.000001"
                    min="0"
                    placeholder="12.50"
                    required
                    value={priceUsdc}
                    onChange={(event) => setPriceUsdc(event.target.value)}
                  />
                  {priceEquivalent !== null && (
                    <p className="text-xs text-muted-foreground">
                      ~ {formatCurrencyAmount(priceEquivalent, displayCurrency)}
                    </p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="display-currency">
                    Display Currency
                  </Label>
                  <DisplayCurrencySelector
                    value={displayCurrency}
                    onChange={setDisplayCurrency}
                    title="Display currency"
                    buttonClassName="w-full justify-between"
                  />
                  <p className="text-xs text-muted-foreground">
                    Quotes only. Settlement stays in USDC on-chain.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Upload Dataset File</CardTitle>
              <CardDescription>
                Upload your CSV dataset for embedding generation
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="csv-file">Dataset File (CSV)</Label>
                <div className="border-2 border-dashed rounded-lg p-8 text-center hover:border-primary/50 transition-colors cursor-pointer">
                  <FileUp className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground mb-2">
                    Click to upload or drag and drop
                  </p>
                  <Input
                    id="csv-file"
                    type="file"
                    accept=".csv"
                    className="hidden"
                    ref={fileInputRef}
                    onChange={(event) =>
                      setFile(event.target.files?.[0] ?? null)
                    }
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    Choose File
                  </Button>
                  {file && (
                    <p className="text-xs text-muted-foreground mt-2">
                      Selected: {file.name}
                    </p>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {(loading || jobStatus || persistedSession || error) && (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <CardTitle>Upload Status</CardTitle>
                    {jobStatus?.status === "completed" &&
                      jobStatus.started_at &&
                      jobStatus.completed_at && (
                        <span className="text-xs text-muted-foreground">
                          Duration:{" "}
                          {formatDuration(
                            new Date(jobStatus.started_at).getTime(),
                            new Date(jobStatus.completed_at).getTime(),
                          )}
                        </span>
                      )}
                  </div>
                  <Badge variant="outline" className={statusMeta.badgeClass}>
                    <span
                      className={`h-2 w-2 rounded-full ${statusMeta.dotClass} animate-pulse`}
                    />
                    {statusMeta.label}
                  </Badge>
                </div>
                <CardDescription>
                  Track embedding job status and outputs
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4 text-sm">
                {loading && (
                  <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-amber-800">
                    <AlertTriangle className="h-4 w-4 mt-0.5" />
                    <span>
                      Upload and embedding can take a while depending on file
                      size.
                    </span>
                  </div>
                )}
                {error && (
                  <ErrorPanel title="Operation failed" message={error} />
                )}

                {(job || persistedSession) && (
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Job ID</p>
                    <div className="flex items-center gap-2">
                      <code className="flex-1 bg-muted px-3 py-2 rounded font-mono text-xs break-all">
                        {job?.job_id ?? persistedSession?.jobId}
                      </code>
                      <Button
                        variant="outline"
                        size="icon"
                        onClick={() =>
                          copyToClipboard(
                            job?.job_id ?? persistedSession?.jobId ?? "",
                            "Job ID",
                          )
                        }
                      >
                        <Copy className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                )}

                {currentListingId && (
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Listing ID</p>
                    <div className="flex items-center gap-2">
                      <code className="flex-1 bg-muted px-3 py-2 rounded font-mono text-xs break-all">
                        {currentListingId}
                      </code>
                      <Button
                        variant="outline"
                        size="icon"
                        onClick={() =>
                          copyToClipboard(currentListingId, "Listing ID")
                        }
                      >
                        <Copy className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                )}
                {currentDatasetUrl && (
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Dataset URL</p>
                    <div className="flex items-center gap-2">
                      <code className="flex-1 bg-muted px-3 py-2 rounded font-mono text-xs break-all">
                        {currentDatasetUrl}
                      </code>
                      <Button
                        variant="outline"
                        size="icon"
                        onClick={() =>
                          copyToClipboard(currentDatasetUrl, "Dataset URL")
                        }
                      >
                        <Copy className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                )}
                {currentSignatureUrl && (
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">
                      Signature URL
                    </p>
                    <div className="flex items-center gap-2">
                      <code className="flex-1 bg-muted px-3 py-2 rounded font-mono text-xs break-all">
                        {currentSignatureUrl}
                      </code>
                      <Button
                        variant="outline"
                        size="icon"
                        onClick={() =>
                          copyToClipboard(currentSignatureUrl, "Signature URL")
                        }
                      >
                        <Copy className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {effectiveStatus === "completed" && currentListingId && (
            <Card>
              <CardHeader>
                <CardTitle>Create Listing On-Chain</CardTitle>
                <CardDescription>
                  Sign the on-chain listing transaction with your wallet.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                {walletMismatch && (
                  <ErrorPanel
                    title="Wallet mismatch"
                    message={`This pending listing belongs to ${persistedSession?.seller}. Connect that address to sign createItem.`}
                  />
                )}
                <div className="space-y-1">
                  <p className="text-xs text-muted-foreground">Listing UUID</p>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 rounded bg-muted px-3 py-2 font-mono text-xs break-all">
                      {currentListingId}
                    </code>
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() =>
                        copyToClipboard(currentListingId, "Listing UUID")
                      }
                    >
                      <Copy className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                <div className="space-y-1">
                  <p className="text-xs text-muted-foreground">
                    Listing Bytes32
                  </p>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 rounded bg-muted px-3 py-2 font-mono text-xs break-all">
                      {uuidToBytes32(currentListingId)}
                    </code>
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() =>
                        copyToClipboard(
                          uuidToBytes32(currentListingId),
                          "Listing Bytes32",
                        )
                      }
                    >
                      <Copy className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                {createTxHash && (
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Create Tx</p>
                    <div className="flex items-center gap-2">
                      <code className="flex-1 rounded bg-muted px-3 py-2 font-mono text-xs break-all">
                        {createTxHash}
                      </code>
                      <Button
                        variant="outline"
                        size="icon"
                        onClick={() =>
                          copyToClipboard(createTxHash, "Create Tx Hash")
                        }
                      >
                        <Copy className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                )}
                <div className="flex justify-between gap-3">
                  <Button
                    variant="outline"
                    type="button"
                    onClick={clearPendingSession}
                  >
                    Discard Session
                  </Button>
                  <Button
                    type="button"
                    className="gap-2 sm:w-auto"
                    disabled={isCreating || walletMismatch}
                    onClick={async () => {
                      if (!address) {
                        setError("Connect wallet to create item.");
                        return;
                      }
                      if (!currentDatasetUrl || !currentDatasetHash) {
                        setError("Missing dataset upload outputs.");
                        return;
                      }
                      if (!currentSignatureUrl || !currentSignatureHash) {
                        setError("Missing signature upload outputs.");
                        return;
                      }
                      if (
                        !priceAtomic &&
                        !persistedSession?.priceAtomic &&
                        !persistedSession?.priceWei
                      ) {
                        setError("Missing price.");
                        return;
                      }

                      const datasetId = await createItemOnChain(address);
                      if (datasetId) {
                        navigate(`/dataset/${datasetId}`);
                      }
                    }}
                  >
                    {isCreating ? (
                      <>
                        <LoaderCircle className="h-4 w-4 animate-spin" />
                        Creating...
                      </>
                    ) : (
                      <>
                        <PenLine className="h-4 w-4" />
                        Create Item
                      </>
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          <div className="flex justify-end gap-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => navigate("/")}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              className="gap-2"
              disabled={loading || hasSubmitted}
            >
              {hasSubmitted ? (
                <>
                  <BadgeCheck className="h-4 w-4" />
                  Listed
                </>
              ) : loading ? (
                <>
                  <LoaderCircle className="h-4 w-4 animate-spin" />
                  Uploading...
                </>
              ) : (
                <>
                  <UploadIcon className="h-4 w-4" />
                  List Dataset
                </>
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default Upload;
