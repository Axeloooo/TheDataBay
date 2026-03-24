"""
Pydantic schemas for agentic layer endpoints.
"""

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class AgentCreateRequest(BaseModel):
    """Request model for creating a new agent."""

    handle: str = Field(..., max_length=64, description="Unique handle for the agent")
    display_name: str = Field(..., description="Display name of the agent")
    bio: Optional[str] = Field(None, description="Biography or description of the agent")
    avatar_url: Optional[str] = Field(None, description="URL to the agent's avatar image")
    homepage_url: Optional[str] = Field(None, description="URL to the agent's homepage")
    capability_tags: List[str] = Field(
        default_factory=list, description="List of capability tags describing the agent"
    )
    owner_address: Optional[str] = Field(None, description="Ethereum address of the agent owner")


class AgentUpdateRequest(BaseModel):
    """Request model for updating an existing agent."""

    display_name: Optional[str] = Field(None, description="Display name of the agent")
    bio: Optional[str] = Field(None, description="Biography or description of the agent")
    avatar_url: Optional[str] = Field(None, description="URL to the agent's avatar image")
    homepage_url: Optional[str] = Field(None, description="URL to the agent's homepage")
    capability_tags: Optional[List[str]] = Field(
        None, description="List of capability tags describing the agent"
    )
    owner_address: Optional[str] = Field(None, description="Ethereum address of the agent owner")


class AgentResponse(BaseModel):
    """Response model for a single agent."""

    id: UUID = Field(..., description="Unique identifier (UUID)")
    handle: str = Field(..., description="Unique handle for the agent")
    display_name: str = Field(..., description="Display name of the agent")
    bio: Optional[str] = Field(None, description="Biography or description of the agent")
    avatar_url: Optional[str] = Field(None, description="URL to the agent's avatar image")
    homepage_url: Optional[str] = Field(None, description="URL to the agent's homepage")
    capability_tags: List[str] = Field(
        default_factory=list, description="List of capability tags describing the agent"
    )
    verification_status: str = Field(..., description="Verification status of the agent")
    owner_address: Optional[str] = Field(None, description="Ethereum address of the agent owner")
    is_active: bool = Field(..., description="Whether the agent is active")
    created_at: datetime = Field(..., description="Timestamp when the agent was created")
    updated_at: datetime = Field(..., description="Timestamp when the agent was last updated")

    @field_validator("capability_tags", mode="before")
    @classmethod
    def parse_capability_tags(cls, v):
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v


class AgentListResponse(BaseModel):
    """Response model for listing agents."""

    agents: List[AgentResponse] = Field(..., description="List of agents")
    count: int = Field(..., description="Number of agents in this response")
    total: int = Field(..., description="Total number of agents available")


class RecommendationResponse(BaseModel):
    """Response model for a single recommendation."""

    id: UUID = Field(..., description="Unique identifier (UUID)")
    agent_id: UUID = Field(..., description="ID of the agent making the recommendation")
    listing_id: str = Field(..., description="ID of the recommended listing")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    similarity_score: Optional[float] = Field(
        None, ge=-1.0, le=1.0, description="Similarity score between agent and listing (-1 to 1)"
    )
    rationale: str = Field(..., description="Explanation for the recommendation")
    pros: List[str] = Field(default_factory=list, description="Pros or advantages of this listing")
    cons: List[str] = Field(default_factory=list, description="Cons or disadvantages of this listing")
    suggested_use_cases: List[str] = Field(
        default_factory=list, description="Suggested use cases for this listing"
    )
    is_retracted: bool = Field(
        default=False, description="Whether the recommendation has been retracted"
    )
    created_at: datetime = Field(..., description="Timestamp when the recommendation was created")
    updated_at: datetime = Field(..., description="Timestamp when the recommendation was last updated")

    @field_validator("pros", "cons", "suggested_use_cases", mode="before")
    @classmethod
    def parse_list_fields(cls, v):
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v


class RecommendationListResponse(BaseModel):
    """Response model for listing recommendations."""

    recommendations: List[RecommendationResponse] = Field(..., description="List of recommendations")
    count: int = Field(..., description="Number of recommendations in this response")
    total: int = Field(..., description="Total number of recommendations available")


class PurchaseRequestCreate(BaseModel):
    """Request model for creating a purchase request."""

    listing_id: str = Field(..., description="ID of the listing to request")
    requester_address: str = Field(..., description="Ethereum address of the requester")
    reason: str = Field(..., max_length=500, description="Reason for the purchase request")


class PurchaseRequestReview(BaseModel):
    """Request model for reviewing a purchase request."""

    status: str = Field(
        ...,
        description="Review status (must be 'approved' or 'rejected')",
        pattern="^(approved|rejected)$"
    )
    reviewed_by: str = Field(..., description="Ethereum address of the reviewer")


class PurchaseRequestResponse(BaseModel):
    """Response model for a single purchase request."""

    id: UUID = Field(..., description="Unique identifier (UUID)")
    agent_id: UUID = Field(..., description="ID of the agent receiving the request")
    listing_id: str = Field(..., description="ID of the requested listing")
    requester_address: str = Field(..., description="Ethereum address of the requester")
    status: Literal["pending", "approved", "rejected"] = Field(..., description="Status of the purchase request")
    reason: str = Field(..., description="Reason for the purchase request")
    reviewed_at: Optional[datetime] = Field(None, description="Timestamp when the request was reviewed")
    reviewed_by: Optional[str] = Field(None, description="Ethereum address of the reviewer")
    created_at: datetime = Field(..., description="Timestamp when the request was created")
    updated_at: datetime = Field(..., description="Timestamp when the request was last updated")


class PurchaseRequestListResponse(BaseModel):
    """Response model for listing purchase requests."""

    requests: List[PurchaseRequestResponse] = Field(..., description="List of purchase requests")
    count: int = Field(..., description="Number of requests in this response")
    total: int = Field(..., description="Total number of purchase requests available")
