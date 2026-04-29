"""
Repository functions for Agent, AgentRecommendation, and AgentPurchaseRequest models.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session, select, func, or_, col

from ..models.agent import Agent, AgentRecommendation, AgentPurchaseRequest
from .schemas import AgentCreateRequest, AgentUpdateRequest

# ---------------------------------------------------------------------------
# Agent functions
# ---------------------------------------------------------------------------


def create_agent(session: Session, data: AgentCreateRequest) -> Agent:
    """Create a new agent record.

    Args:
        session: Database session
        data: AgentCreateRequest schema with agent fields

    Returns:
        Agent: The newly created Agent record
    """
    now = datetime.now(timezone.utc)
    agent = Agent(
        handle=data.handle,
        display_name=data.display_name,
        bio=data.bio,
        avatar_url=data.avatar_url,
        homepage_url=data.homepage_url,
        capability_tags=json.dumps(data.capability_tags),
        owner_address=data.owner_address,
        created_at=now,
        updated_at=now,
    )
    session.add(agent)
    session.commit()
    session.refresh(agent)
    return agent


def get_agent_by_handle(session: Session, handle: str) -> Optional[Agent]:
    """Retrieve an agent by its unique handle.

    Args:
        session: Database session
        handle: Unique handle string

    Returns:
        Optional[Agent]: Agent record or None if not found
    """
    statement = select(Agent).where(Agent.handle == handle)
    return session.exec(statement).first()


def list_agents(
    session: Session,
    search: Optional[str] = None,
    tag: Optional[str] = None,
    status: Optional[str] = None,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[Agent], int]:
    """List agents with optional filtering.

    Args:
        session: Database session
        search: Case-insensitive substring match on handle or display_name
        tag: Filter by tag present in capability_tags JSON string
        status: Filter by verification_status
        offset: Pagination offset
        limit: Maximum number of results

    Returns:
        tuple[list[Agent], int]: (agents, total_count)
    """
    statement = select(Agent)
    count_statement = select(func.count()).select_from(Agent)

    if search is not None:
        search_lower = f"%{search.lower()}%"
        search_filter = or_(
            func.lower(Agent.handle).like(search_lower),
            func.lower(Agent.display_name).like(search_lower),
        )
        statement = statement.where(search_filter)
        count_statement = count_statement.where(search_filter)

    if tag is not None:
        tag_filter = col(Agent.capability_tags).contains(f'"{tag}"')
        statement = statement.where(tag_filter)
        count_statement = count_statement.where(tag_filter)

    if status is not None:
        statement = statement.where(Agent.verification_status == status)
        count_statement = count_statement.where(Agent.verification_status == status)

    total = session.exec(count_statement).one()
    agents = session.exec(statement.offset(offset).limit(limit)).all()
    return list(agents), total


def update_agent(session: Session, agent: Agent, data: AgentUpdateRequest) -> Agent:
    """Update an existing agent with non-None fields from the request.

    Args:
        session: Database session
        agent: Existing Agent record to update
        data: AgentUpdateRequest with fields to update (None fields are skipped)

    Returns:
        Agent: The updated Agent record
    """
    now = datetime.now(timezone.utc)

    if data.display_name is not None:
        agent.display_name = data.display_name
    if data.bio is not None:
        agent.bio = data.bio
    if data.avatar_url is not None:
        agent.avatar_url = data.avatar_url
    if data.homepage_url is not None:
        agent.homepage_url = data.homepage_url
    if data.capability_tags is not None:
        agent.capability_tags = json.dumps(data.capability_tags)
    if data.owner_address is not None:
        agent.owner_address = data.owner_address

    agent.updated_at = now
    session.add(agent)
    session.commit()
    session.refresh(agent)
    return agent


def deactivate_agent(session: Session, agent: Agent) -> Agent:
    """Mark an agent as inactive.

    Args:
        session: Database session
        agent: Agent record to deactivate

    Returns:
        Agent: The deactivated Agent record
    """
    agent.is_active = False
    agent.updated_at = datetime.now(timezone.utc)
    session.add(agent)
    session.commit()
    session.refresh(agent)
    return agent


# ---------------------------------------------------------------------------
# Recommendation functions
# ---------------------------------------------------------------------------


def create_recommendation(
    session: Session,
    agent_id: uuid.UUID,
    listing_id: str,
    confidence: float,
    similarity_score: Optional[float],
    rationale: str,
    pros: list[str],
    cons: list[str],
    suggested_use_cases: list[str],
) -> AgentRecommendation:
    """Create a new agent recommendation record.

    Args:
        session: Database session
        agent_id: UUID of the recommending agent
        listing_id: On-chain listing identifier
        confidence: Confidence score (0.0–1.0)
        similarity_score: Optional semantic similarity score
        rationale: Human-readable explanation for the recommendation
        pros: List of advantages
        cons: List of disadvantages
        suggested_use_cases: List of suggested use cases

    Returns:
        AgentRecommendation: The newly created record
    """
    now = datetime.now(timezone.utc)
    rec = AgentRecommendation(
        agent_id=agent_id,
        listing_id=listing_id,
        confidence=confidence,
        similarity_score=similarity_score,
        rationale=rationale,
        pros=json.dumps(pros),
        cons=json.dumps(cons),
        suggested_use_cases=json.dumps(suggested_use_cases),
        created_at=now,
        updated_at=now,
    )
    session.add(rec)
    session.commit()
    session.refresh(rec)
    return rec


def list_recommendations(
    session: Session,
    agent_id: Optional[uuid.UUID] = None,
    listing_id: Optional[str] = None,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[AgentRecommendation], int]:
    """List recommendations with optional filtering.

    Args:
        session: Database session
        agent_id: Filter by agent UUID
        listing_id: Filter by listing ID
        offset: Pagination offset
        limit: Maximum number of results

    Returns:
        tuple[list[AgentRecommendation], int]: (recommendations, total_count)
    """
    statement = select(AgentRecommendation)
    count_statement = select(func.count()).select_from(AgentRecommendation)

    if agent_id is not None:
        statement = statement.where(AgentRecommendation.agent_id == agent_id)
        count_statement = count_statement.where(
            AgentRecommendation.agent_id == agent_id
        )

    if listing_id is not None:
        statement = statement.where(AgentRecommendation.listing_id == listing_id)
        count_statement = count_statement.where(
            AgentRecommendation.listing_id == listing_id
        )

    total = session.exec(count_statement).one()
    recs = session.exec(statement.offset(offset).limit(limit)).all()
    return list(recs), total


def get_recommendation_by_id(
    session: Session, rec_id: uuid.UUID
) -> Optional[AgentRecommendation]:
    """Get a recommendation by its primary key ID.

    Args:
        session: Database session
        rec_id: UUID primary key of the recommendation

    Returns:
        Optional[AgentRecommendation]: Recommendation record or None if not found
    """
    return session.get(AgentRecommendation, rec_id)


def retract_recommendation(
    session: Session, rec: AgentRecommendation
) -> AgentRecommendation:
    """Mark a recommendation as retracted.

    Args:
        session: Database session
        rec: AgentRecommendation record to retract

    Returns:
        AgentRecommendation: The retracted record
    """
    rec.is_retracted = True
    rec.updated_at = datetime.now(timezone.utc)
    session.add(rec)
    session.commit()
    session.refresh(rec)
    return rec


# ---------------------------------------------------------------------------
# Purchase request functions
# ---------------------------------------------------------------------------


def create_purchase_request(
    session: Session,
    agent_id: uuid.UUID,
    listing_id: str,
    requester_address: str,
    reason: str,
) -> AgentPurchaseRequest:
    """Create a new agent purchase request.

    Args:
        session: Database session
        agent_id: UUID of the requesting agent
        listing_id: On-chain listing identifier
        requester_address: Wallet address that will pay
        reason: Reason for the purchase request

    Returns:
        AgentPurchaseRequest: The newly created record
    """
    now = datetime.now(timezone.utc)
    req = AgentPurchaseRequest(
        agent_id=agent_id,
        listing_id=listing_id,
        requester_address=requester_address,
        reason=reason,
        created_at=now,
        updated_at=now,
    )
    session.add(req)
    session.commit()
    session.refresh(req)
    return req


def list_purchase_requests(
    session: Session,
    agent_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    requester_address: Optional[str] = None,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[AgentPurchaseRequest], int]:
    """List purchase requests with optional filtering.

    Args:
        session: Database session
        agent_id: Filter by agent UUID
        status: Filter by status ("pending" | "approved" | "rejected")
        requester_address: Filter by requester wallet address
        offset: Pagination offset
        limit: Maximum number of results

    Returns:
        tuple[list[AgentPurchaseRequest], int]: (requests, total_count)
    """
    statement = select(AgentPurchaseRequest)
    count_statement = select(func.count()).select_from(AgentPurchaseRequest)

    if agent_id is not None:
        statement = statement.where(AgentPurchaseRequest.agent_id == agent_id)
        count_statement = count_statement.where(
            AgentPurchaseRequest.agent_id == agent_id
        )

    if status is not None:
        statement = statement.where(AgentPurchaseRequest.status == status)
        count_statement = count_statement.where(AgentPurchaseRequest.status == status)

    if requester_address is not None:
        statement = statement.where(
            AgentPurchaseRequest.requester_address == requester_address
        )
        count_statement = count_statement.where(
            AgentPurchaseRequest.requester_address == requester_address
        )

    total = session.exec(count_statement).one()
    reqs = session.exec(statement.offset(offset).limit(limit)).all()
    return list(reqs), total


def get_purchase_request_by_id(
    session: Session, request_id: uuid.UUID
) -> Optional[AgentPurchaseRequest]:
    """Get a purchase request by its primary key ID.

    Args:
        session: Database session
        request_id: UUID primary key of the purchase request

    Returns:
        Optional[AgentPurchaseRequest]: Purchase request record or None if not found
    """
    return session.get(AgentPurchaseRequest, request_id)


def review_purchase_request(
    session: Session,
    req: AgentPurchaseRequest,
    status: str,
    reviewed_by: str,
) -> AgentPurchaseRequest:
    """Update a purchase request with a review decision.

    Args:
        session: Database session
        req: AgentPurchaseRequest record to review
        status: New status ("approved" or "rejected")
        reviewed_by: Wallet address of the reviewer

    Returns:
        AgentPurchaseRequest: The reviewed record
    """
    now = datetime.now(timezone.utc)
    req.status = status
    req.reviewed_by = reviewed_by
    req.reviewed_at = now
    req.updated_at = now
    session.add(req)
    session.commit()
    session.refresh(req)
    return req
