"""
SQLModel for agentic integration layer.

Defines Agent, AgentRecommendation, and AgentPurchaseRequest models
for autonomous agent participation in the BridgeMart marketplace.
"""

from datetime import datetime, timezone
import uuid
from typing import Optional

from sqlmodel import SQLModel, Field


class Agent(SQLModel, table=True):
    """Autonomous agent profile and metadata."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    handle: str = Field(unique=True, index=True, max_length=64)
    display_name: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    homepage_url: Optional[str] = None
    capability_tags: str = "[]"  # JSON-as-TEXT, stores list[str]
    verification_status: str = "unverified"  # "unverified" | "self_attested" | "platform_verified"
    owner_address: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentRecommendation(SQLModel, table=True):
    """Agent recommendation of a marketplace listing."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    agent_id: uuid.UUID = Field(foreign_key="agent.id", index=True)
    listing_id: str = Field(index=True)  # on-chain ref
    confidence: float  # 0.0-1.0
    similarity_score: Optional[float] = None
    rationale: str  # max 1000
    pros: str = "[]"  # JSON-as-TEXT list
    cons: str = "[]"  # JSON-as-TEXT list
    suggested_use_cases: str = "[]"  # JSON-as-TEXT list
    is_retracted: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentPurchaseRequest(SQLModel, table=True):
    """Agent-initiated purchase request for a listing."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    agent_id: uuid.UUID = Field(foreign_key="agent.id", index=True)
    listing_id: str = Field(index=True)
    requester_address: str  # wallet that will pay
    status: str = "pending"  # "pending" | "approved" | "rejected"
    reason: str  # max 500
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None  # address of approver/rejector
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
