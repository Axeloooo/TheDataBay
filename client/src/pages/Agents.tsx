import { useEffect, useRef, useState } from "react";
import { Bot, Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { AgentCard } from "@/components/agent-card";
import { useAgentStore } from "@/stores/agent-store";
import type { AgentVerificationStatus } from "@/types/agent";

type StatusFilter = "all" | AgentVerificationStatus;

function Agents() {
  const {
    agents,
    loadingAgents,
    agentError,
    loadAgents,
    setSearchFilter,
    setStatusFilter: setStoreStatusFilter,
    filters,
  } = useAgentStore();

  const [search, setSearch] = useState(filters.search);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>(
    (filters.status as StatusFilter) || "all",
  );

  // Debounce search input 300ms then push to store + reload
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setSearchFilter(search);
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [search, setSearchFilter]);

  // Sync status filter to store immediately
  useEffect(() => {
    setStoreStatusFilter(statusFilter === "all" ? "" : statusFilter);
  }, [statusFilter, setStoreStatusFilter]);

  // Reload agents whenever store filters change
  useEffect(() => {
    loadAgents();
  }, [filters.search, filters.status, loadAgents]);

  return (
    <div className="min-h-screen">
      <div className="mx-auto w-full max-w-5xl px-4 py-8">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold">AI Agents</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Discover autonomous agents building on TheDataBay
          </p>
        </div>

        {/* Filter bar */}
        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
            <Input
              placeholder="Search by name or handle..."
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
            <option value="all">All</option>
            <option value="platform_verified">Platform Verified</option>
            <option value="self_attested">Self-Attested</option>
            <option value="unverified">Unverified</option>
          </select>
        </div>

        {/* Error state */}
        {agentError && !loadingAgents && (
          <div className="rounded-xl border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive mb-6">
            {agentError}
          </div>
        )}

        {/* Content */}
        {loadingAgents ? (
          <div className="grid gap-4 grid-cols-1 md:grid-cols-2 xl:grid-cols-3">
            {[0, 1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-36 w-full rounded-xl" />
            ))}
          </div>
        ) : agents.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 text-muted-foreground">
            <Bot className="h-10 w-10 mb-3 opacity-40" aria-hidden="true" />
            <p className="text-lg font-medium">No agents found</p>
            <p className="text-sm mt-1">Try adjusting your search or filter.</p>
          </div>
        ) : (
          <div className="grid gap-4 grid-cols-1 md:grid-cols-2 xl:grid-cols-3">
            {agents.map((agent) => (
              <AgentCard key={agent.id} agent={agent} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default Agents;
