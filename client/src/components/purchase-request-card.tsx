import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CheckCircle, XCircle, Clock } from "lucide-react";
import type { PurchaseRequest } from "@/types/agent";
import { cn } from "@/lib/utils";

interface PurchaseRequestCardProps {
  request: PurchaseRequest;
  connectedAddress?: string | null;
  onApprove?: (id: string) => void;
  onReject?: (id: string) => void;
  className?: string;
}

const STATUS_CONFIG = {
  pending: { label: "Pending Review", variant: "outline" as const, icon: Clock },
  approved: { label: "Approved", variant: "default" as const, icon: CheckCircle },
  rejected: { label: "Rejected", variant: "destructive" as const, icon: XCircle },
};

export function PurchaseRequestCard({
  request,
  connectedAddress,
  onApprove,
  onReject,
  className,
}: PurchaseRequestCardProps) {
  const config = STATUS_CONFIG[request.status];
  const StatusIcon = config.icon;
  const canReview = request.status === "pending" && !!connectedAddress;

  return (
    <div className={cn("rounded-xl border border-border/80 bg-card/65 p-4 shadow-sm", className)}>
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="min-w-0">
          <p className="text-sm font-medium truncate">Dataset: {request.listing_id}</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            Requested by: <span className="font-mono">{request.requester_address.slice(0, 10)}...{request.requester_address.slice(-6)}</span>
          </p>
        </div>
        <Badge variant={config.variant} className="gap-1 shrink-0">
          <StatusIcon className="h-3 w-3" />
          {config.label}
        </Badge>
      </div>

      <p className="text-sm text-muted-foreground mb-3">{request.reason}</p>

      {request.reviewed_by && (
        <p className="text-xs text-muted-foreground mb-3">
          Reviewed by: <span className="font-mono">{request.reviewed_by.slice(0, 10)}...{request.reviewed_by.slice(-6)}</span>
        </p>
      )}

      {canReview && (
        <div className="flex gap-2 mt-2">
          <Button
            size="sm"
            className="flex-1 gap-1.5 bg-green-600 hover:bg-green-700 text-white text-xs"
            onClick={() => onApprove?.(request.id)}
          >
            <CheckCircle className="h-3.5 w-3.5" />
            Approve
          </Button>
          <Button
            size="sm"
            variant="destructive"
            className="flex-1 gap-1.5 text-xs"
            onClick={() => onReject?.(request.id)}
          >
            <XCircle className="h-3.5 w-3.5" />
            Reject
          </Button>
        </div>
      )}
    </div>
  );
}
