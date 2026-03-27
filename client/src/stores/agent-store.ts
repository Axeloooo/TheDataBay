import { create } from "zustand";
import { backend } from "@/lib/backend";
import type { Agent, AgentRecommendation, PurchaseRequest } from "@/types/agent";

type AgentFilters = {
  search: string;
  tag: string;
  status: string;
};

type AgentStore = {
  // State
  agents: Agent[];
  selectedAgent: Agent | null;
  recommendations: AgentRecommendation[];
  purchaseRequests: PurchaseRequest[];
  totalAgents: number;
  totalPurchaseRequests: number;
  loadingAgents: boolean;
  loadingAgent: boolean;
  loadingRecommendations: boolean;
  loadingPurchaseRequests: boolean;
  agentError: string | null;
  purchaseRequestError: string | null;
  filters: AgentFilters;

  // Actions
  loadAgents: () => Promise<void>;
  loadAgent: (handle: string) => Promise<void>;
  loadPurchaseRequests: (status?: string) => Promise<void>;
  clearSelectedAgent: () => void;
  setSearchFilter: (search: string) => void;
  setTagFilter: (tag: string) => void;
  setStatusFilter: (status: string) => void;
  clearFilters: () => void;
};

let agentsRequestSeq = 0;
let agentDetailRequestSeq = 0;
let purchaseRequestsSeq = 0;

export const useAgentStore = create<AgentStore>()((set, get) => ({
  agents: [],
  selectedAgent: null,
  recommendations: [],
  purchaseRequests: [],
  totalAgents: 0,
  totalPurchaseRequests: 0,
  loadingAgents: false,
  loadingAgent: false,
  loadingRecommendations: false,
  loadingPurchaseRequests: false,
  agentError: null,
  purchaseRequestError: null,
  filters: { search: "", tag: "", status: "" },

  loadAgents: async () => {
    const { filters } = get();
    const requestId = ++agentsRequestSeq;
    set({ loadingAgents: true, agentError: null });
    try {
      const res = await backend.getAgents({
        search: filters.search || undefined,
        tag: filters.tag || undefined,
        status: filters.status || undefined,
      });
      if (requestId !== agentsRequestSeq) return;
      set({ agents: res.agents, totalAgents: res.total, loadingAgents: false });
    } catch (err) {
      if (requestId !== agentsRequestSeq) return;
      set({ agentError: err instanceof Error ? err.message : "Failed to load agents", loadingAgents: false });
    }
  },

  loadAgent: async (handle: string) => {
    const requestId = ++agentDetailRequestSeq;
    set({ loadingAgent: true, loadingRecommendations: true, agentError: null });

    // First, load the agent itself.
    try {
      const agent = await backend.getAgent(handle);
      if (requestId !== agentDetailRequestSeq) return;
      set({ selectedAgent: agent, loadingAgent: false });
    } catch (err) {
      if (requestId !== agentDetailRequestSeq) return;
      set({
        agentError: err instanceof Error ? err.message : "Failed to load agent",
        loadingAgent: false,
        loadingRecommendations: false,
      });
      return;
    }

    // Then, load recommendations separately so failures here don't present as agent-load failures.
    try {
      const recsRes = await backend.getAgentRecommendations(handle);
      if (requestId !== agentDetailRequestSeq) return;
      set({ recommendations: recsRes.recommendations, loadingRecommendations: false });
    } catch (err) {
      // Log the recommendations error but don't overwrite a successful agent load.
      console.error("Failed to load agent recommendations", err);
      if (requestId !== agentDetailRequestSeq) return;
      set({ loadingRecommendations: false });
    }
  },

  loadPurchaseRequests: async (status?: string) => {
    const requestId = ++purchaseRequestsSeq;
    set({ loadingPurchaseRequests: true, purchaseRequestError: null });
    try {
      const res = await backend.getPurchaseRequests({ status });
      if (requestId !== purchaseRequestsSeq) return;
      set({ purchaseRequests: res.requests, totalPurchaseRequests: res.total, loadingPurchaseRequests: false });
    } catch (err) {
      if (requestId !== purchaseRequestsSeq) return;
      set({ purchaseRequestError: err instanceof Error ? err.message : "Failed to load purchase requests", loadingPurchaseRequests: false });
    }
  },

  clearSelectedAgent: () => set({ selectedAgent: null, recommendations: [] }),

  setSearchFilter: (search) => set((state) => ({ filters: { ...state.filters, search } })),
  setTagFilter: (tag) => set((state) => ({ filters: { ...state.filters, tag } })),
  setStatusFilter: (status) => set((state) => ({ filters: { ...state.filters, status } })),
  clearFilters: () => set({ filters: { search: "", tag: "", status: "" } }),
}));
