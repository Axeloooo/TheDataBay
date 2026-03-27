import { Badge } from "@/components/ui/badge";
import { CheckCircle, Circle, AlertCircle } from "lucide-react";
import type { AgentVerificationStatus } from "@/types/agent";
import { cn } from "@/lib/utils";

interface AgentBadgeProps {
  status: AgentVerificationStatus;
  className?: string;
}

export function AgentBadge({ status, className }: AgentBadgeProps) {
  if (status === "platform_verified") {
    return (
      <Badge className={cn("gap-1 bg-green-100 text-green-800 border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-800", className)}>
        <CheckCircle className="h-3 w-3" aria-hidden="true" />
        Platform Verified
      </Badge>
    );
  }
  if (status === "self_attested") {
    return (
      <Badge className={cn("gap-1 bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-400 dark:border-yellow-800", className)}>
        <AlertCircle className="h-3 w-3" aria-hidden="true" />
        Self-Attested
      </Badge>
    );
  }
  return (
    <Badge variant="outline" className={cn("gap-1 text-muted-foreground", className)}>
      <Circle className="h-3 w-3" aria-hidden="true" />
      Unverified
    </Badge>
  );
}
