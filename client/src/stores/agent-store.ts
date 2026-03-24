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
  setSearchFilter: (search: string) => void;
  setTagFilter: (tag: string) => void;
  setStatusFilter: (status: string) => void;
  clearFilters: () => void;
};

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
    set({ loadingAgents: true, agentError: null });
    try {
      const res = await backend.getAgents({
        search: filters.search || undefined,
        tag: filters.tag || undefined,
        status: filters.status || undefined,
      });
      set({ agents: res.agents, totalAgents: res.total, loadingAgents: false });
    } catch (err) {
      set({ agentError: err instanceof Error ? err.message : "Failed to load agents", loadingAgents: false });
    }
  },

  loadAgent: async (handle: string) => {
    set({ loadingAgent: true, loadingRecommendations: true, agentError: null });
    try {
      const agent = await backend.getAgent(handle);
      set({ selectedAgent: agent, loadingAgent: false });
      const recsRes = await backend.getAgentRecommendations(handle);
      set({ recommendations: recsRes.recommendations, loadingRecommendations: false });
    } catch (err) {
      set({ agentError: err instanceof Error ? err.message : "Failed to load agent", loadingAgent: false, loadingRecommendations: false });
    }
  },

  loadPurchaseRequests: async (status?: string) => {
    set({ loadingPurchaseRequests: true, purchaseRequestError: null });
    try {
      const res = await backend.getPurchaseRequests({ status });
      set({ purchaseRequests: res.requests, totalPurchaseRequests: res.total, loadingPurchaseRequests: false });
    } catch (err) {
      set({ purchaseRequestError: err instanceof Error ? err.message : "Failed to load purchase requests", loadingPurchaseRequests: false });
    }
  },

  setSearchFilter: (search) => set((state) => ({ filters: { ...state.filters, search } })),
  setTagFilter: (tag) => set((state) => ({ filters: { ...state.filters, tag } })),
  setStatusFilter: (status) => set((state) => ({ filters: { ...state.filters, status } })),
  clearFilters: () => set({ filters: { search: "", tag: "", status: "" } }),
}));
