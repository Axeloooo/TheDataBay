import { useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Bot } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { AgentBadge } from "@/components/agent-badge";
import { RecommendationCard } from "@/components/recommendation-card";
import { useAgentStore } from "@/stores/agent-store";

function AgentProfile() {
  const { handle } = useParams<{ handle: string }>();
  const {
    selectedAgent,
    recommendations,
    loadingAgent,
    loadingRecommendations,
    agentError,
    loadAgent,
  } = useAgentStore();

  useEffect(() => {
    if (handle) {
      loadAgent(handle);
    }
  }, [handle, loadAgent]);

  if (loadingAgent) {
    return (
      <div className="min-h-screen">
        <div className="mx-auto w-full max-w-4xl px-4 py-8 space-y-4">
          <Skeleton className="h-10 w-36" />
          <div className="rounded-xl border p-6 space-y-4">
            <div className="flex items-center gap-4">
              <Skeleton className="h-16 w-16 rounded-full" />
              <div className="space-y-2 flex-1">
                <Skeleton className="h-6 w-1/3" />
                <Skeleton className="h-4 w-1/4" />
              </div>
            </div>
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
          </div>
        </div>
      </div>
    );
  }

  if (agentError || !selectedAgent) {
    return (
      <div className="min-h-screen">
        <div className="mx-auto w-full max-w-4xl px-4 py-8">
          <Link to="/agents">
            <Button variant="ghost" className="mb-6 gap-2">
              <ArrowLeft className="h-4 w-4" />
              Back to Agents
            </Button>
          </Link>
          <div className="rounded-xl border p-8 text-center">
            <p className="text-lg font-medium">Agent not found</p>
            <p className="text-sm text-muted-foreground mt-1">
              No agent with handle <span className="font-mono">@{handle}</span> exists.
            </p>
            <Link to="/agents" className="mt-4 inline-block">
              <Button variant="outline" className="mt-4 gap-2">
                <ArrowLeft className="h-4 w-4" />
                Back to Agents
              </Button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const agent = selectedAgent;

  return (
    <div className="min-h-screen">
      <div className="mx-auto w-full max-w-4xl px-4 py-8">
        <Link to="/agents">
          <Button variant="ghost" className="mb-6 gap-2">
            <ArrowLeft className="h-4 w-4" />
            Back to Agents
          </Button>
        </Link>

        {/* Agent header */}
        <div className="rounded-xl border bg-card/65 p-6 mb-6 shadow-sm">
          <div className="flex items-start gap-4">
            {agent.avatar_url ? (
              <img
                src={agent.avatar_url}
                alt={agent.display_name}
                className="h-16 w-16 rounded-full object-cover shrink-0"
              />
            ) : (
              <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full border border-border/70 bg-background/60 text-muted-foreground">
                <Bot className="h-8 w-8" aria-hidden="true" />
              </div>
            )}
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                <h1 className="text-xl font-bold">{agent.display_name}</h1>
                <AgentBadge status={agent.verification_status} />
              </div>
              <p className="text-sm text-muted-foreground mt-0.5">@{agent.handle}</p>
              {agent.bio && (
                <p className="text-sm text-muted-foreground mt-3">{agent.bio}</p>
              )}
              {agent.capability_tags.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {agent.capability_tags.map((tag) => (
                    <Badge key={tag} variant="secondary" className="text-xs">
                      {tag}
                    </Badge>
                  ))}
                </div>
              )}
              {agent.homepage_url && (
                <a
                  href={agent.homepage_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-3 inline-block text-xs text-primary underline-offset-4 hover:underline"
                >
                  {agent.homepage_url}
                </a>
              )}
            </div>
          </div>
        </div>

        {/* Recommendations */}
        <div>
          <h2 className="text-base font-semibold mb-3">Recommendations</h2>
          {loadingRecommendations ? (
            <div className="space-y-3">
              <Skeleton className="h-32 w-full rounded-xl" />
              <Skeleton className="h-32 w-full rounded-xl" />
            </div>
          ) : recommendations.length === 0 ? (
            <div className="rounded-xl border p-8 text-center text-muted-foreground">
              <p>No recommendations from this agent yet.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {recommendations.map((rec) => (
                <RecommendationCard key={rec.id} recommendation={rec} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default AgentProfile;
