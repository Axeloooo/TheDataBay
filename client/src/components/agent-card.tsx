import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { AgentBadge } from "@/components/agent-badge";
import { Bot } from "lucide-react";
import type { Agent } from "@/types/agent";
import { cn } from "@/lib/utils";

interface AgentCardProps {
  agent: Agent;
  className?: string;
}

export function AgentCard({ agent, className }: AgentCardProps) {
  return (
    <Link
      to={`/agents/${agent.handle}`}
      className={cn(
        "block rounded-xl border border-border/80 bg-card/65 p-4 shadow-sm transition hover:border-primary/50 hover:bg-card",
        className,
      )}
    >
      <div className="flex items-start gap-3">
        {agent.avatar_url ? (
          <img
            src={agent.avatar_url}
            alt={agent.display_name}
            className="h-10 w-10 rounded-full object-cover shrink-0"
          />
        ) : (
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-border/70 bg-background/60 text-muted-foreground">
            <Bot className="h-5 w-5" aria-hidden="true" />
          </div>
        )}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-sm leading-tight">
              {agent.display_name}
            </span>
            <AgentBadge status={agent.verification_status} />
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            @{agent.handle}
          </p>
          {agent.bio && (
            <p className="text-xs text-muted-foreground mt-1.5 line-clamp-2">
              {agent.bio}
            </p>
          )}
          {agent.capability_tags.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {agent.capability_tags.slice(0, 4).map((tag) => (
                <Badge
                  key={tag}
                  variant="secondary"
                  className="text-[10px] h-5 px-1.5"
                >
                  {tag}
                </Badge>
              ))}
              {agent.capability_tags.length > 4 && (
                <Badge variant="secondary" className="text-[10px] h-5 px-1.5">
                  +{agent.capability_tags.length - 4}
                </Badge>
              )}
            </div>
          )}
        </div>
      </div>
    </Link>
  );
}
