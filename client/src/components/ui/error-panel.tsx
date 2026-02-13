import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ErrorPanelProps {
  title: string;
  message: string;
  onRetry?: () => void;
  retryLabel?: string;
}

function ErrorPanel({
  title,
  message,
  onRetry,
  retryLabel = "Try again",
}: ErrorPanelProps) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-900">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-5 w-5" />
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-semibold">{title}</h3>
          <p className="mt-1 text-sm text-red-800 break-words">{message}</p>
          {onRetry && (
            <Button
              variant="outline"
              className="mt-3 border-red-300 bg-red-100/70 text-red-900 hover:bg-red-100 dark:border-red-500/40 dark:bg-red-950/30 dark:text-red-200 dark:hover:bg-red-950/50"
              onClick={onRetry}
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              {retryLabel}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

export default ErrorPanel;
