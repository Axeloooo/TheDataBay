"""
Router exposing agentic layer operations: agent registry, recommendations, purchase requests.
"""

import uuid
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from ..config.settings import Settings, get_settings
from ..database.engine import get_session
from ..services.agent_repo import (
    create_agent,
    get_agent_by_handle,
    list_agents,
    update_agent,
    deactivate_agent,
    create_recommendation,
    list_recommendations,
    retract_recommendation as retract_recommendation_repo,
    create_purchase_request,
    list_purchase_requests,
    review_purchase_request as review_purchase_request_repo,
)
from ..services.agent_service import generate_recommendation as generate_recommendation_service
from ..services.ai_service import AIService, get_ai_service
from ..services.rate_limiter import agent_write_rate_limiter
from ..schemas.agent_schema import (
    AgentCreateRequest,
    AgentUpdateRequest,
    AgentResponse,
    AgentListResponse,
    RecommendationResponse,
    RecommendationListResponse,
    PurchaseRequestCreate,
    PurchaseRequestReview,
    PurchaseRequestResponse,
    PurchaseRequestListResponse,
)

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])
purchase_router = APIRouter(prefix="/api/v1/purchase-requests", tags=["purchase-requests"])
rec_router = APIRouter(prefix="/api/v1/recommendations", tags=["recommendations"])

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Agent CRUD
# ---------------------------------------------------------------------------


@router.post("/", response_model=AgentResponse, status_code=201)
def register_agent(
    data: AgentCreateRequest,
    session: Session = Depends(get_session),
    _: None = Depends(agent_write_rate_limiter),
):
    """Register a new agent.

    Args:
        data (AgentCreateRequest): Agent creation payload.
        session (Session): Database session.

    Returns:
        AgentResponse: Created agent record.
    """
    existing = get_agent_by_handle(session, data.handle)
    if existing:
        raise HTTPException(status_code=409, detail="Handle already taken")
    agent = create_agent(session, data)
    return agent


@router.get("/", response_model=AgentListResponse)
def list_agents_route(
    search: Optional[str] = None,
    tag: Optional[str] = None,
    status: Optional[str] = None,
    offset: int = 0,
    limit: int = 20,
    session: Session = Depends(get_session),
):
    """List agents with optional filters.

    Args:
        search (str, optional): Full-text search query.
        tag (str, optional): Filter by capability tag.
        status (str, optional): Filter by verification status.
        offset (int): Pagination offset.
        limit (int): Page size.
        session (Session): Database session.

    Returns:
        AgentListResponse: Paginated list of agents.
    """
    agents, total = list_agents(session, search=search, tag=tag, status=status, offset=offset, limit=limit)
    return AgentListResponse(agents=agents, count=len(agents), total=total)


@router.get("/{handle}", response_model=AgentResponse)
def get_agent(handle: str, session: Session = Depends(get_session)):
    """Get a single agent by handle.

    Args:
        handle (str): Unique agent handle.
        session (Session): Database session.

    Returns:
        AgentResponse: Agent record.
    """
    agent = get_agent_by_handle(session, handle)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.patch("/{handle}", response_model=AgentResponse)
def update_agent_route(
    handle: str,
    data: AgentUpdateRequest,
    session: Session = Depends(get_session),
    _: None = Depends(agent_write_rate_limiter),
):
    """Update an agent's profile.

    Args:
        handle (str): Unique agent handle.
        data (AgentUpdateRequest): Fields to update.
        session (Session): Database session.

    Returns:
        AgentResponse: Updated agent record.
    """
    agent = get_agent_by_handle(session, handle)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return update_agent(session, agent, data)


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------


@router.post("/{handle}/recommend", response_model=RecommendationResponse)
async def generate_recommendation_route(
    handle: str,
    body: dict,
    session: Session = Depends(get_session),
    ai_service: AIService = Depends(get_ai_service),
    settings: Settings = Depends(get_settings),
    _: None = Depends(agent_write_rate_limiter),
):
    """Generate a recommendation for a dataset query on behalf of an agent.

    Args:
        handle (str): Unique agent handle.
        body (dict): Request body containing ``query`` key.
        session (Session): Database session.
        ai_service (AIService): AI service instance.
        settings (Settings): Application settings.

    Returns:
        RecommendationResponse: Generated recommendation.
    """
    agent = get_agent_by_handle(session, handle)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    query = body.get("query", "").strip()
    if not query:
        raise HTTPException(status_code=422, detail="query is required")
    result = await generate_recommendation_service(agent.id, query, session, ai_service, settings)
    if result is None:
        raise HTTPException(status_code=404, detail="No matching datasets found for query")
    return result


@router.get("/{handle}/recommendations", response_model=RecommendationListResponse)
def list_agent_recommendations(
    handle: str,
    offset: int = 0,
    limit: int = 20,
    session: Session = Depends(get_session),
):
    """List recommendations made by an agent.

    Args:
        handle (str): Unique agent handle.
        offset (int): Pagination offset.
        limit (int): Page size.
        session (Session): Database session.

    Returns:
        RecommendationListResponse: Paginated list of recommendations.
    """
    agent = get_agent_by_handle(session, handle)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    recs, total = list_recommendations(session, agent_id=agent.id, offset=offset, limit=limit)
    return RecommendationListResponse(recommendations=recs, count=len(recs), total=total)


@router.post("/{handle}/recommendations/{rec_id}/retract", response_model=RecommendationResponse)
def retract_recommendation_route(
    handle: str,
    rec_id: uuid.UUID,
    session: Session = Depends(get_session),
    _: None = Depends(agent_write_rate_limiter),
):
    """Retract a recommendation made by an agent.

    Args:
        handle (str): Unique agent handle.
        rec_id (uuid.UUID): Recommendation UUID to retract.
        session (Session): Database session.

    Returns:
        RecommendationResponse: Updated recommendation marked as retracted.
    """
    agent = get_agent_by_handle(session, handle)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    recs, _ = list_recommendations(session, agent_id=agent.id)
    rec = next((r for r in recs if r.id == rec_id), None)
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return retract_recommendation_repo(session, rec)


# ---------------------------------------------------------------------------
# Purchase Requests (agent-scoped)
# ---------------------------------------------------------------------------


@router.post("/{handle}/purchase-requests", response_model=PurchaseRequestResponse, status_code=201)
def submit_purchase_request(
    handle: str,
    data: PurchaseRequestCreate,
    session: Session = Depends(get_session),
    _: None = Depends(agent_write_rate_limiter),
):
    """Submit a purchase request on behalf of an agent.

    Args:
        handle (str): Unique agent handle.
        data (PurchaseRequestCreate): Purchase request payload.
        session (Session): Database session.

    Returns:
        PurchaseRequestResponse: Created purchase request.
    """
    agent = get_agent_by_handle(session, handle)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    req = create_purchase_request(session, agent.id, data.listing_id, data.requester_address, data.reason)
    return req


@router.get("/{handle}/purchase-requests", response_model=PurchaseRequestListResponse)
def list_agent_purchase_requests(
    handle: str,
    status: Optional[str] = None,
    offset: int = 0,
    limit: int = 20,
    session: Session = Depends(get_session),
):
    """List purchase requests submitted by an agent.

    Args:
        handle (str): Unique agent handle.
        status (str, optional): Filter by request status.
        offset (int): Pagination offset.
        limit (int): Page size.
        session (Session): Database session.

    Returns:
        PurchaseRequestListResponse: Paginated list of purchase requests.
    """
    agent = get_agent_by_handle(session, handle)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    reqs, total = list_purchase_requests(session, agent_id=agent.id, status=status, offset=offset, limit=limit)
    return PurchaseRequestListResponse(requests=reqs, count=len(reqs), total=total)


# ---------------------------------------------------------------------------
# Purchase Requests (global)
# ---------------------------------------------------------------------------


@purchase_router.get("/", response_model=PurchaseRequestListResponse)
def list_all_purchase_requests(
    status: Optional[str] = "pending",
    offset: int = 0,
    limit: int = 20,
    session: Session = Depends(get_session),
):
    """List all purchase requests across all agents.

    Args:
        status (str, optional): Filter by request status. Defaults to 'pending'.
        offset (int): Pagination offset.
        limit (int): Page size.
        session (Session): Database session.

    Returns:
        PurchaseRequestListResponse: Paginated list of purchase requests.
    """
    reqs, total = list_purchase_requests(session, status=status, offset=offset, limit=limit)
    return PurchaseRequestListResponse(requests=reqs, count=len(reqs), total=total)


@purchase_router.post("/{request_id}/review", response_model=PurchaseRequestResponse)
def review_purchase_request_route(
    request_id: uuid.UUID,
    data: PurchaseRequestReview,
    session: Session = Depends(get_session),
):
    """Review (approve or reject) a purchase request.

    Args:
        request_id (uuid.UUID): Purchase request UUID.
        data (PurchaseRequestReview): Review decision payload.
        session (Session): Database session.

    Returns:
        PurchaseRequestResponse: Updated purchase request.
    """
    reqs, _ = list_purchase_requests(session)
    req = next((r for r in reqs if r.id == request_id), None)
    if not req:
        raise HTTPException(status_code=404, detail="Purchase request not found")
    return review_purchase_request_repo(session, req, data.status, data.reviewed_by)


# ---------------------------------------------------------------------------
# Recommendations (by listing — separate prefix to avoid /{handle} conflict)
# ---------------------------------------------------------------------------


@rec_router.get("/by-listing/{listing_id}", response_model=RecommendationListResponse)
def get_recommendations_for_listing(
    listing_id: str,
    offset: int = 0,
    limit: int = 20,
    session: Session = Depends(get_session),
):
    """Get all recommendations for a specific listing.

    Args:
        listing_id (str): Marketplace listing ID.
        offset (int): Pagination offset.
        limit (int): Page size.
        session (Session): Database session.

    Returns:
        RecommendationListResponse: Paginated list of recommendations for the listing.
    """
    recs, total = list_recommendations(session, listing_id=listing_id, offset=offset, limit=limit)
    return RecommendationListResponse(recommendations=recs, count=len(recs), total=total)
