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
import { useWallet } from "@/providers/wallet-provider";
import { useNavigate } from "react-router-dom";
import { useEffect, useMemo, useRef, useState } from "react";
import { backend } from "@/lib/backend";
import type { JobResponse, JobStatusResponse } from "@/types/llm";
import { createItemTx } from "@/lib/marketplace";
import { uuidToBytes32 } from "@/lib/ids";
import { toast } from "sonner";
import ErrorPanel from "@/components/ui/error-panel";
import { fireConfettiBurst } from "@/lib/confetti";
import {
  clearUploadSession,
  loadUploadSession,
  saveUploadSession,
  type PersistedUploadSession,
} from "@/lib/upload-session";
import {
  convertEthToCurrency,
  formatCurrencyAmount,
  type DisplayCurrency,
} from "@/lib/fx";
import { useCurrency } from "@/context/currency-context";

function Upload() {
  const { isConnected, address, connect } = useWallet();
  const { preferredCurrency, rates } = useCurrency();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollTimerRef = useRef<number | null>(null);
  const previousStatusRef = useRef<string | null>(null);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priceEth, setPriceEth] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [job, setJob] = useState<JobResponse | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatusResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createTxHash, setCreateTxHash] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [persistedSession, setPersistedSession] = useState<PersistedUploadSession | null>(null);
  const [payCurrency, setPayCurrency] = useState<DisplayCurrency>(preferredCurrency);
  const hasSubmitted = !!job || !!persistedSession;

  useEffect(() => {
    setPayCurrency(preferredCurrency);
  }, [preferredCurrency]);

  useEffect(() => {
    const session = loadUploadSession();
    if (!session) return;

    setPersistedSession(session);
    setTitle(session.title);
    setDescription(session.description);
    if (session.priceWei) {
      const whole = BigInt(session.priceWei) / 10n ** 18n;
      const frac = (BigInt(session.priceWei) % 10n ** 18n).toString().padStart(18, "0");
      setPriceEth(`${whole}.${frac}`.replace(/\.?0+$/, ""));
    }
    if (session.jobId) {
      setJob({
        job_id: session.jobId,
        listing_id: session.listingId ?? "",
        status: session.status ?? "queued",
      });
    }
    if (
      session.listingId &&
      session.status &&
      (session.status === "completed" || session.status === "failed")
    ) {
      setJobStatus((current) => {
        if (current) return current;
        return {
          job_id: session.jobId,
          status: session.status ?? "queued",
          listing_id: session.listingId,
          created_at: session.createdAt,
          started_at: null,
          completed_at: null,
          filename: session.fileName ?? "dataset.csv",
          error: session.error,
          dataset_url: session.datasetUrl,
          dataset_hash: session.datasetHash,
          signature: session.signatureUrl && session.signatureHash
            ? {
                signature_url: session.signatureUrl,
                signature_hash: session.signatureHash,
              }
            : undefined,
        };
      });
    }
    previousStatusRef.current = session.status ?? null;
  }, []);

  useEffect(() => {
    return () => {
      if (pollTimerRef.current) {
        window.clearInterval(pollTimerRef.current);
      }
    };
  }, []);

  const syncSessionFromStatus = (
    status: JobStatusResponse,
    current: PersistedUploadSession,
  ): PersistedUploadSession => {
    const updated: PersistedUploadSession = {
      ...current,
      listingId: status.listing_id ?? current.listingId,
      status: status.status as PersistedUploadSession["status"],
      datasetUrl: status.dataset_url ?? current.datasetUrl,
      datasetHash: status.dataset_hash ?? current.datasetHash,
      signatureUrl: status.signature?.signature_url ?? current.signatureUrl,
      signatureHash: status.signature?.signature_hash ?? current.signatureHash,
      error: status.error ?? current.error,
      updatedAt: new Date().toISOString(),
    };
    saveUploadSession(updated);
    setPersistedSession(updated);
    return updated;
  };

  const maybeNotifyTerminalStatus = (status: JobStatusResponse, session: PersistedUploadSession) => {
    if (status.status !== "completed" && status.status !== "failed") return;
    if (session.toastNotifiedStatus === status.status) return;

    if (status.status === "completed") {
      toast.success("Embedding job completed", {
        description: "Dataset encrypted and uploaded. Ready to sign on-chain listing.",
      });
    } else {
      toast.error("Embedding job failed", {
        description: status.error ?? "Review the error details and retry.",
      });
    }

    const updated: PersistedUploadSession = {
      ...session,
      toastNotifiedStatus: status.status,
      updatedAt: new Date().toISOString(),
    };
    saveUploadSession(updated);
    setPersistedSession(updated);
  };

  const pollJob = async (jobId: string) => {
    let status: JobStatusResponse;
    try {
      status = await backend.getJobStatus(jobId);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to fetch job status";
      if (message.toLowerCase().includes("job not found")) {
        setError(
          "Session found, but job is no longer available on server memory. If upload already completed, you can still sign if required fields are present.",
        );
      } else {
        setError(message);
      }
      setLoading(false);
      return false;
    }
    setJobStatus(status);
    const session = loadUploadSession();
    if (session && session.jobId === jobId) {
      const synced = syncSessionFromStatus(status, session);
      maybeNotifyTerminalStatus(status, synced);
    }

    const prev = previousStatusRef.current;
    if (prev !== status.status) {
      previousStatusRef.current = status.status;
    }

    if (status.status === "completed" || status.status === "failed") {
      if (pollTimerRef.current) {
        window.clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
      setLoading(false);
      return false;
    }
    return true;
  };

  useEffect(() => {
    const activeJobId = job?.job_id ?? persistedSession?.jobId;
    const activeStatus = jobStatus?.status ?? persistedSession?.status;
    if (!activeJobId) return;
    if (activeStatus === "completed" || activeStatus === "failed") return;

    setLoading(true);
    void pollJob(activeJobId);
    pollTimerRef.current = window.setInterval(() => {
      void pollJob(activeJobId).catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to poll job status");
        setLoading(false);
      });
    }, 8000);

    return () => {
      if (pollTimerRef.current) {
        window.clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };
  }, [job?.job_id, persistedSession?.jobId, jobStatus?.status, persistedSession?.status]);

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

  const priceWei = useMemo(() => {
    if (!priceEth) return null;
    const [whole, fraction = ""] = priceEth.split(".");
    const fracPadded = (fraction + "0".repeat(18)).slice(0, 18);
    try {
      return (BigInt(whole || "0") * 10n ** 18n + BigInt(fracPadded || "0")).toString();
    } catch {
      return null;
    }
  }, [priceEth]);

  const priceEquivalent = useMemo(() => {
    if (!priceEth || payCurrency === "ETH") return null;
    const ethValue = Number(priceEth);
    if (!Number.isFinite(ethValue)) return null;
    return convertEthToCurrency(ethValue, payCurrency, rates);
  }, [payCurrency, priceEth, rates]);

  const currentListingId = jobStatus?.listing_id ?? persistedSession?.listingId ?? null;
  const currentDatasetUrl = jobStatus?.dataset_url ?? persistedSession?.datasetUrl;
  const currentDatasetHash = jobStatus?.dataset_hash ?? persistedSession?.datasetHash;
  const currentSignatureUrl =
    jobStatus?.signature?.signature_url ?? persistedSession?.signatureUrl;
  const currentSignatureHash =
    jobStatus?.signature?.signature_hash ?? persistedSession?.signatureHash;
  const effectiveStatus = jobStatus?.status ?? persistedSession?.status;
  const walletMismatch =
    !!address &&
    !!persistedSession?.seller &&
    persistedSession.seller.toLowerCase() !== address.toLowerCase();

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

  const clearPendingSession = () => {
    clearUploadSession();
    setPersistedSession(null);
    setJob(null);
    setJobStatus(null);
    setCreateTxHash(null);
    setError(null);
    setLoading(false);
    previousStatusRef.current = null;
  };

  if (!isConnected) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center px-4 py-8">
        <div className="w-full max-w-2xl rounded-2xl border bg-card p-8 shadow-sm">
          <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl border bg-muted">
            <Wallet className="h-6 w-6" />
          </div>
          <h1 className="text-2xl font-bold">Connect Wallet to List Datasets</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Listing requires an Ethereum wallet signature. Connect your wallet to upload,
            encrypt, and publish datasets on-chain.
          </p>
          <p className="mt-2 text-xs text-muted-foreground">
            Solana wallet connection is planned for upcoming cross-chain support.
          </p>
          <div className="mt-6 flex flex-col gap-3 sm:flex-row">
            <Button className="gap-2" onClick={() => void connect()}>
              <Wallet className="h-4 w-4" />
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
            List your dataset with embeddings on the marketplace and earn ETH from sales.
          </p>
        </div>

        {(persistedSession && !jobStatus) && (
          <div className="mb-4 flex items-center justify-between rounded-lg border bg-amber-50 p-3 text-sm text-amber-900">
            <span>
              Resumed pending upload session for listing {persistedSession.listingId ?? "pending"}.
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
            setError(null);

            if (!address) {
              setError("Connect wallet to continue.");
              return;
            }
            if (!file) {
              setError("Select a dataset file.");
              return;
            }
            if (!priceWei) {
              setError("Enter a valid price.");
              return;
            }

            const formData = new FormData();
            formData.append("file", file);
            formData.append("title", title);
            formData.append("description", description);
            formData.append("seller", address);
            formData.append("price", priceWei);
            formData.append("seller_wallet_type", "evm");

            setLoading(true);
            try {
              const response = await backend.submitEmbedBatch(formData);
              setJob(response);
              const session: PersistedUploadSession = {
                jobId: response.job_id,
                listingId: response.listing_id ?? null,
                title,
                description,
                seller: address,
                priceWei,
                fileName: file.name,
                status: "queued",
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString(),
                toastNotifiedStatus: null,
              };
              saveUploadSession(session);
              setPersistedSession(session);
              await pollJob(response.job_id);
            } catch (err) {
              setError(err instanceof Error ? err.message : "Upload failed");
              setLoading(false);
            }
          }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Basic Information</CardTitle>
              <CardDescription>Provide details about your dataset</CardDescription>
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
                  <Label htmlFor="price">Price (ETH)</Label>
                  <Input
                    id="price"
                    type="number"
                    step="0.0001"
                    min="0"
                    placeholder="0.05"
                    required
                    value={priceEth}
                    onChange={(event) => setPriceEth(event.target.value)}
                  />
                  {priceEquivalent !== null && (
                    <p className="text-xs text-muted-foreground">
                      ~ {formatCurrencyAmount(priceEquivalent, payCurrency)}
                    </p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="pay-currency">Preferred Display Currency</Label>
                  <select
                    id="pay-currency"
                    value={payCurrency}
                    onChange={(event) => setPayCurrency(event.target.value as DisplayCurrency)}
                    className="h-10 w-full rounded-md border bg-background px-3 text-sm"
                  >
                    <option value="ETH">ETH</option>
                    <option value="CAD">CAD</option>
                    <option value="USD">USD</option>
                    <option value="EUR">EUR</option>
                    <option value="USDC">USDC</option>
                    <option value="SOL">SOL</option>
                  </select>
                  <p className="text-xs text-muted-foreground">
                    Execution currently uses ETH/wei on-chain.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Upload Dataset File</CardTitle>
              <CardDescription>Upload your CSV dataset for embedding generation</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="csv-file">Dataset File (CSV)</Label>
                <div className="border-2 border-dashed rounded-lg p-8 text-center hover:border-primary/50 transition-colors cursor-pointer">
                  <FileUp className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground mb-2">Click to upload or drag and drop</p>
                  <Input
                    id="csv-file"
                    type="file"
                    accept=".csv"
                    className="hidden"
                    ref={fileInputRef}
                    onChange={(event) => setFile(event.target.files?.[0] ?? null)}
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
                    <p className="text-xs text-muted-foreground mt-2">Selected: {file.name}</p>
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
                    <span className={`h-2 w-2 rounded-full ${statusMeta.dotClass} animate-pulse`} />
                    {statusMeta.label}
                  </Badge>
                </div>
                <CardDescription>Track embedding job status and outputs</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4 text-sm">
                {loading && (
                  <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-amber-800">
                    <AlertTriangle className="h-4 w-4 mt-0.5" />
                    <span>Upload and embedding can take a while depending on file size.</span>
                  </div>
                )}
                {error && <ErrorPanel title="Operation failed" message={error} />}

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
                        onClick={() => copyToClipboard(job?.job_id ?? persistedSession?.jobId ?? "", "Job ID")}
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
                        onClick={() => copyToClipboard(currentListingId, "Listing ID")}
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
                        onClick={() => copyToClipboard(currentDatasetUrl, "Dataset URL")}
                      >
                        <Copy className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                )}
                {currentSignatureUrl && (
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Signature URL</p>
                    <div className="flex items-center gap-2">
                      <code className="flex-1 bg-muted px-3 py-2 rounded font-mono text-xs break-all">
                        {currentSignatureUrl}
                      </code>
                      <Button
                        variant="outline"
                        size="icon"
                        onClick={() => copyToClipboard(currentSignatureUrl, "Signature URL")}
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
                      onClick={() => copyToClipboard(currentListingId, "Listing UUID")}
                    >
                      <Copy className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                <div className="space-y-1">
                  <p className="text-xs text-muted-foreground">Listing Bytes32</p>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 rounded bg-muted px-3 py-2 font-mono text-xs break-all">
                      {uuidToBytes32(currentListingId)}
                    </code>
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => copyToClipboard(uuidToBytes32(currentListingId), "Listing Bytes32")}
                    >
                      <Copy className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                <div className="flex justify-between gap-3">
                  <Button variant="outline" type="button" onClick={clearPendingSession}>
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
                      const effectivePriceWei = persistedSession?.priceWei ?? priceWei;
                      if (!effectivePriceWei) {
                        setError("Missing price.");
                        return;
                      }
                      setError(null);
                      setIsCreating(true);
                      try {
                        const txHash = await createItemTx({
                          listingId: currentListingId,
                          title: persistedSession?.title ?? title,
                          description: persistedSession?.description ?? description,
                          seller: address,
                          priceWei: effectivePriceWei,
                          datasetUrl: currentDatasetUrl,
                          datasetHash: currentDatasetHash,
                          signatureUrl: currentSignatureUrl,
                          signatureHash: currentSignatureHash,
                        });
                        setCreateTxHash(txHash);
                        toast.success("Listing created on-chain", { description: txHash });
                        fireConfettiBurst();
                        clearUploadSession();
                        setPersistedSession(null);
                        navigate(`/dataset/${uuidToBytes32(currentListingId)}`);
                      } catch (err) {
                        setError(err instanceof Error ? err.message : "Failed to create item");
                      } finally {
                        setIsCreating(false);
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
                {createTxHash && (
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Create Tx</p>
                    <div className="flex items-center gap-2">
                      <code className="flex-1 bg-muted px-3 py-2 rounded font-mono text-xs break-all">
                        {createTxHash}
                      </code>
                      <Button
                        variant="outline"
                        size="icon"
                        onClick={() => copyToClipboard(createTxHash, "Create Tx Hash")}
                      >
                        <Copy className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          <div className="flex justify-end gap-4">
            <Button type="button" variant="outline" onClick={() => navigate("/")}>
              Cancel
            </Button>
            <Button type="submit" className="gap-2" disabled={loading || hasSubmitted}>
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
