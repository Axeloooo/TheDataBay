import { useEffect, useState } from "react";
import { Bot } from "lucide-react";
import { backend } from "@/lib/backend";
import { RecommendationCard } from "@/components/recommendation-card";
import { Skeleton } from "@/components/ui/skeleton";
import type { AgentRecommendation } from "@/types/agent";

interface DatasetRecommendationsProps {
  listingId: string;
}

export function DatasetRecommendations({ listingId }: DatasetRecommendationsProps) {
  const [recommendations, setRecommendations] = useState<AgentRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [, setError] = useState(false);

  useEffect(() => {
    let active = true;
    backend
      .getRecommendationsForListing(listingId)
      .then((res) => {
        if (!active) return;
        setRecommendations(res.recommendations);
      })
      .catch((err) => {
        console.error("Failed to load recommendations:", err);
        if (!active) return;
        setError(true);
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [listingId]);

  if (loading) {
    return (
      <div className="mt-6">
        <div className="flex items-center gap-2 mb-3">
          <Bot className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium">Agent Recommendations</span>
        </div>
        <div className="space-y-3">
          <Skeleton className="h-32 w-full" />
        </div>
      </div>
    );
  }

  if (recommendations.length === 0) return null;

  return (
    <div className="mt-6">
      <div className="flex items-center gap-2 mb-3">
        <Bot className="h-4 w-4 text-muted-foreground" />
        <span className="text-sm font-medium">Agent Recommendations</span>
        <span className="text-xs text-muted-foreground">({recommendations.length})</span>
      </div>
      <div className="space-y-3">
        {recommendations.map((rec) => (
          <RecommendationCard key={rec.id} recommendation={rec} />
        ))}
      </div>
    </div>
  );
}
