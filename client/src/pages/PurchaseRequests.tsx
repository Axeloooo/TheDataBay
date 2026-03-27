import { useEffect, useState } from "react";
import { ShoppingCart } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { PurchaseRequestCard } from "@/components/purchase-request-card";
import { backend } from "@/lib/backend";
import { useAgentStore } from "@/stores/agent-store";
import { useWalletStore } from "@/stores/wallet-store";
import type { PurchaseRequest, PurchaseRequestStatus } from "@/types/agent";
import { toast } from "sonner";

type StatusFilter = "all" | PurchaseRequestStatus;

const STATUS_OPTIONS: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "pending", label: "Pending" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
];

function PurchaseRequests() {
  const {
    purchaseRequests,
    loadingPurchaseRequests,
    purchaseRequestError,
    loadPurchaseRequests,
  } = useAgentStore((state) => ({
    purchaseRequests: state.purchaseRequests,
    loadingPurchaseRequests: state.loadingPurchaseRequests,
    purchaseRequestError: state.purchaseRequestError,
    loadPurchaseRequests: state.loadPurchaseRequests,
  }));
  const address = useWalletStore((state) => state.address);

  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");

  // Count pending requests for the badge
  const pendingCount = purchaseRequests.filter(
    (r: PurchaseRequest) => r.status === "pending",
  ).length;

  useEffect(() => {
    loadPurchaseRequests(statusFilter === "all" ? undefined : statusFilter);
  }, [statusFilter, loadPurchaseRequests]);

  const handleApprove = async (id: string) => {
    try {
      await backend.reviewPurchaseRequest(id, {
        status: "approved",
        reviewed_by: address ?? "unknown",
      });
      loadPurchaseRequests(statusFilter === "all" ? undefined : statusFilter);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to approve request.";
      toast.error(message);
    }
  };

  const handleReject = async (id: string) => {
    try {
      await backend.reviewPurchaseRequest(id, {
        status: "rejected",
        reviewed_by: address ?? "unknown",
      });
      loadPurchaseRequests(statusFilter === "all" ? undefined : statusFilter);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to reject request.";
      toast.error(message);
    }
  };

  return (
    <div className="min-h-screen">
      <div className="mx-auto w-full max-w-4xl px-4 py-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold">Purchase Requests</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Review and approve AI agent purchase requests
            </p>
          </div>

          {/* Status filter with pending badge */}
          <div className="flex items-center gap-2">
            {pendingCount > 0 && statusFilter !== "pending" && (
              <Badge variant="outline" className="shrink-0">
                {pendingCount} pending
              </Badge>
            )}
            <select
              value={statusFilter}
              onChange={(e) =>
                setStatusFilter(e.target.value as StatusFilter)
              }
              className="h-10 rounded-md border border-input bg-background px-3 text-sm w-full sm:w-48"
            >
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                  {opt.value === "pending" && pendingCount > 0
                    ? ` (${pendingCount})`
                    : ""}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Error state */}
        {purchaseRequestError && !loadingPurchaseRequests && (
          <div className="rounded-xl border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive mb-6">
            {purchaseRequestError}
          </div>
        )}

        {/* Content */}
        {loadingPurchaseRequests ? (
          <div className="space-y-4">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-28 w-full rounded-xl" />
            ))}
          </div>
        ) : purchaseRequests.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 text-muted-foreground">
            <ShoppingCart
              className="h-10 w-10 mb-3 opacity-40"
              aria-hidden="true"
            />
            <p className="text-lg font-medium">No purchase requests</p>
            <p className="text-sm mt-1">
              {statusFilter === "all"
                ? "There are no purchase requests yet."
                : `No ${statusFilter} requests found.`}
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {purchaseRequests.map((request: PurchaseRequest) => (
              <PurchaseRequestCard
                key={request.id}
                request={request}
                connectedAddress={address}
                onApprove={handleApprove}
                onReject={handleReject}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default PurchaseRequests;
