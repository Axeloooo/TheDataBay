import { useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { AgentCard } from "@/components/agent-card";
import { useAgentStore } from "@/stores/agent-store";
import type { AgentVerificationStatus } from "@/types/agent";

type StatusFilter = "all" | AgentVerificationStatus;

function Agents() {
  const { agents, loadingAgents, loadAgents } = useAgentStore();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");

  useEffect(() => {
    loadAgents();
  }, [loadAgents]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return agents.filter((agent) => {
      if (
        q &&
        !agent.display_name.toLowerCase().includes(q) &&
        !agent.handle.toLowerCase().includes(q) &&
        !(agent.bio ?? "").toLowerCase().includes(q)
      ) {
        return false;
      }
      if (statusFilter !== "all" && agent.verification_status !== statusFilter) {
        return false;
      }
      return true;
    });
  }, [agents, search, statusFilter]);

  return (
    <div className="min-h-screen">
      <div className="mx-auto w-full max-w-5xl px-4 py-8">
        <h1 className="text-2xl font-bold mb-6">AI Agents</h1>

        {/* Filter bar */}
        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
            <Input
              placeholder="Search by name, handle, or bio..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
            className="h-10 rounded-md border border-input bg-background px-3 text-sm w-full sm:w-52"
          >
            <option value="all">All statuses</option>
            <option value="platform_verified">Platform Verified</option>
            <option value="self_attested">Self-Attested</option>
            <option value="unverified">Unverified</option>
          </select>
        </div>

        {/* Content */}
        {loadingAgents ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-36 w-full rounded-xl" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 text-muted-foreground">
            <p className="text-lg font-medium">No agents found</p>
            <p className="text-sm mt-1">Try adjusting your search or filter.</p>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {filtered.map((agent) => (
              <AgentCard key={agent.id} agent={agent} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default Agents;
