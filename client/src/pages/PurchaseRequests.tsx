import { useEffect, useState } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { PurchaseRequestCard } from "@/components/purchase-request-card";
import { useAgentStore } from "@/stores/agent-store";
import { useWalletStore } from "@/stores/wallet-store";
import type { PurchaseRequestStatus } from "@/types/agent";

type StatusFilter = "all" | PurchaseRequestStatus;

function PurchaseRequests() {
  const { purchaseRequests, loadingPurchaseRequests, loadPurchaseRequests } =
    useAgentStore();
  const address = useWalletStore((state) => state.address);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");

  useEffect(() => {
    loadPurchaseRequests(statusFilter === "all" ? undefined : statusFilter);
  }, [statusFilter, loadPurchaseRequests]);

  return (
    <div className="min-h-screen">
      <div className="mx-auto w-full max-w-4xl px-4 py-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
          <h1 className="text-2xl font-bold">Purchase Requests</h1>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
            className="h-10 rounded-md border border-input bg-background px-3 text-sm w-full sm:w-48"
          >
            <option value="all">All statuses</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>

        {loadingPurchaseRequests ? (
          <div className="space-y-4">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-28 w-full rounded-xl" />
            ))}
          </div>
        ) : purchaseRequests.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 text-muted-foreground">
            <p className="text-lg font-medium">No purchase requests</p>
            <p className="text-sm mt-1">
              {statusFilter === "all"
                ? "There are no purchase requests yet."
                : `No ${statusFilter} requests found.`}
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {purchaseRequests.map((request) => (
              <PurchaseRequestCard
                key={request.id}
                request={request}
                connectedAddress={address}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default PurchaseRequests;
