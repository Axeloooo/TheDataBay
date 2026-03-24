import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Bot, ThumbsUp, ThumbsDown, ExternalLink } from "lucide-react";
import type { AgentRecommendation } from "@/types/agent";
import { cn } from "@/lib/utils";

interface RecommendationCardProps {
  recommendation: AgentRecommendation;
  className?: string;
}

export function RecommendationCard({ recommendation, className }: RecommendationCardProps) {
  const confidencePct = Math.round(recommendation.confidence * 100);

  return (
    <div className={cn("rounded-xl border border-border/80 bg-card/65 p-4 shadow-sm", recommendation.is_retracted && "opacity-50", className)}>
      {/* Always-visible AI-generated badge */}
      <div className="flex items-center justify-between mb-3">
        <Badge className="gap-1 bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800">
          <Bot className="h-3 w-3" />
          AI-generated
        </Badge>
        {recommendation.is_retracted && (
          <Badge variant="destructive" className="text-xs">Retracted</Badge>
        )}
      </div>

      {/* Confidence bar */}
      <div className="mb-3">
        <div className="flex justify-between text-xs text-muted-foreground mb-1">
          <span>Confidence</span>
          <span className="font-medium">{confidencePct}%</span>
        </div>
        <div className="h-1.5 rounded-full bg-muted overflow-hidden">
          <div
            className={cn(
              "h-full rounded-full transition-all",
              confidencePct >= 70 ? "bg-green-500" : confidencePct >= 40 ? "bg-yellow-500" : "bg-red-400"
            )}
            style={{ width: `${confidencePct}%` }}
          />
        </div>
      </div>

      {/* Rationale */}
      <p className="text-sm text-foreground mb-3">{recommendation.rationale}</p>

      {/* Pros/Cons */}
      {(recommendation.pros.length > 0 || recommendation.cons.length > 0) && (
        <div className="grid grid-cols-2 gap-3 mb-3 text-xs">
          {recommendation.pros.length > 0 && (
            <div>
              <div className="flex items-center gap-1 font-medium text-green-600 dark:text-green-400 mb-1">
                <ThumbsUp className="h-3 w-3" />
                Pros
              </div>
              <ul className="space-y-0.5 text-muted-foreground">
                {recommendation.pros.map((p, i) => <li key={i}>• {p}</li>)}
              </ul>
            </div>
          )}
          {recommendation.cons.length > 0 && (
            <div>
              <div className="flex items-center gap-1 font-medium text-red-600 dark:text-red-400 mb-1">
                <ThumbsDown className="h-3 w-3" />
                Cons
              </div>
              <ul className="space-y-0.5 text-muted-foreground">
                {recommendation.cons.map((c, i) => <li key={i}>• {c}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* CTA — never "Buy", always "Review this dataset" */}
      <Link to={`/dataset/${recommendation.listing_id}`}>
        <Button variant="outline" size="sm" className="w-full gap-1.5 text-xs">
          <ExternalLink className="h-3.5 w-3.5" />
          Review this dataset
        </Button>
      </Link>
    </div>
  );
}
