export type AgentVerificationStatus = "unverified" | "self_attested" | "platform_verified";

export type PurchaseRequestStatus = "pending" | "approved" | "rejected";

export type Agent = {
  id: string; // UUID
  handle: string;
  display_name: string;
  bio: string | null;
  avatar_url: string | null;
  homepage_url: string | null;
  capability_tags: string[];
  verification_status: AgentVerificationStatus;
  owner_address: string | null;
  is_active: boolean;
  created_at: string; // ISO datetime
  updated_at: string;
};

export type AgentListResponse = {
  agents: Agent[];
  count: number;
  total: number;
};

export type AgentRecommendation = {
  id: string; // UUID
  agent_id: string;
  listing_id: string;
  confidence: number; // 0.0-1.0
  similarity_score: number | null;
  rationale: string;
  pros: string[];
  cons: string[];
  suggested_use_cases: string[];
  is_retracted: boolean;
  created_at: string;
  updated_at: string;
};

export type RecommendationListResponse = {
  recommendations: AgentRecommendation[];
  count: number;
  total: number;
};

export type PurchaseRequest = {
  id: string; // UUID
  agent_id: string;
  listing_id: string;
  requester_address: string;
  status: PurchaseRequestStatus;
  reason: string;
  reviewed_at: string | null;
  reviewed_by: string | null;
  created_at: string;
  updated_at: string;
};

export type PurchaseRequestListResponse = {
  requests: PurchaseRequest[];
  count: number;
  total: number;
};
