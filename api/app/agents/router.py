"""
Router exposing agentic layer operations: agent registry, recommendations, purchase requests.
"""

import uuid
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from ..auth.dependencies import AuthedWallet, current_wallet
from ..auth.service import same_evm_address
from ..database.engine import get_session
from .repository import (
    create_agent,
    get_agent_by_handle,
    list_agents,
    update_agent,
    create_recommendation,
    list_recommendations,
    get_recommendation_by_id,
    retract_recommendation as retract_recommendation_repo,
    create_purchase_request,
    list_purchase_requests,
    get_purchase_request_by_id,
    review_purchase_request as review_purchase_request_repo,
)
from .service import (
    generate_recommendation as generate_recommendation_service,
)
from ..ai.service import AIService, get_ai_service
from ..shared.errors import ApiError, ErrorResponse
from ..shared.rate_limiter import agent_write_rate_limiter
from .schemas import (
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
    RecommendQueryRequest,
)

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])
purchase_router = APIRouter(
    prefix="/api/v1/purchase-requests", tags=["purchase-requests"]
)
rec_router = APIRouter(prefix="/api/v1/recommendations", tags=["recommendations"])

logger = logging.getLogger(__name__)

_OWNER_ONLY_RESPONSES = {
    401: {"model": ErrorResponse, "description": "Missing, malformed or expired token"},
    403: {
        "model": ErrorResponse,
        "description": "Signed-in wallet is not the agent's owner_address",
    },
}


def _require_agent_owner(agent, wallet: AuthedWallet, action: str) -> None:
    """Allow an agent write only for the wallet that registered the agent.

    Agents without an owner (legacy or seeded rows) cannot be changed through
    the API at all.
    """
    if not agent.owner_address or not same_evm_address(
        agent.owner_address, wallet.address
    ):
        logger.warning("agents.%s forbidden handle=%s", action, agent.handle)
        raise ApiError(
            status_code=403,
            error="forbidden",
            message="Only the agent's owner wallet can perform this action.",
        )


# ---------------------------------------------------------------------------
# Agent CRUD
# ---------------------------------------------------------------------------


@router.post(
    "/",
    response_model=AgentResponse,
    status_code=201,
    responses={401: _OWNER_ONLY_RESPONSES[401]},
)
def register_agent(
    data: AgentCreateRequest,
    wallet: AuthedWallet = Depends(current_wallet),
    session: Session = Depends(get_session),
    _: None = Depends(agent_write_rate_limiter),
):
    """Register a new agent owned by the signed-in wallet.

    Requires a user-scope bearer token. The token's wallet becomes the agent's
    ``owner_address``; only that wallet can change or act for the agent later.

    Args:
        data (AgentCreateRequest): Agent creation payload.
        wallet (AuthedWallet): Wallet proven by the bearer token.
        session (Session): Database session.

    Returns:
        AgentResponse: Created agent record.
    """
    existing = get_agent_by_handle(session, data.handle)
    if existing:
        raise HTTPException(status_code=409, detail="Handle already taken")
    agent = create_agent(session, data, owner_address=wallet.address)
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
    agents, total = list_agents(
        session, search=search, tag=tag, status=status, offset=offset, limit=limit
    )
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


@router.patch(
    "/{handle}", response_model=AgentResponse, responses=_OWNER_ONLY_RESPONSES
)
def update_agent_route(
    handle: str,
    data: AgentUpdateRequest,
    wallet: AuthedWallet = Depends(current_wallet),
    session: Session = Depends(get_session),
    _: None = Depends(agent_write_rate_limiter),
):
    """Update an agent's profile. Only the agent's owner wallet may do this.

    Args:
        handle (str): Unique agent handle.
        data (AgentUpdateRequest): Fields to update.
        wallet (AuthedWallet): Wallet proven by the bearer token.
        session (Session): Database session.

    Returns:
        AgentResponse: Updated agent record.
    """
    agent = get_agent_by_handle(session, handle)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    _require_agent_owner(agent, wallet, "update")
    return update_agent(session, agent, data)


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------


@router.post(
    "/{handle}/recommend",
    response_model=RecommendationResponse,
    responses=_OWNER_ONLY_RESPONSES,
)
async def generate_recommendation_route(
    handle: str,
    body: RecommendQueryRequest,
    wallet: AuthedWallet = Depends(current_wallet),
    session: Session = Depends(get_session),
    ai_service: AIService = Depends(get_ai_service),
    _: None = Depends(agent_write_rate_limiter),
):
    """Generate a recommendation for a dataset query on behalf of an agent.

    Only the agent's owner wallet may publish recommendations under its name.

    Args:
        handle (str): Unique agent handle.
        body (RecommendQueryRequest): Request body containing ``query`` field.
        wallet (AuthedWallet): Wallet proven by the bearer token.
        session (Session): Database session.
        ai_service (AIService): AI service instance.

    Returns:
        RecommendationResponse: Generated recommendation.
    """
    agent = get_agent_by_handle(session, handle)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    _require_agent_owner(agent, wallet, "recommend")
    query = body.query.strip()
    result = await generate_recommendation_service(
        agent.id, query, session, ai_service
    )
    if result is None:
        raise HTTPException(
            status_code=404, detail="No matching datasets found for query"
        )
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
    recs, total = list_recommendations(
        session, agent_id=agent.id, offset=offset, limit=limit
    )
    return RecommendationListResponse(
        recommendations=recs, count=len(recs), total=total
    )


@router.post(
    "/{handle}/recommendations/{rec_id}/retract",
    response_model=RecommendationResponse,
    responses=_OWNER_ONLY_RESPONSES,
)
def retract_recommendation_route(
    handle: str,
    rec_id: uuid.UUID,
    wallet: AuthedWallet = Depends(current_wallet),
    session: Session = Depends(get_session),
    _: None = Depends(agent_write_rate_limiter),
):
    """Retract a recommendation made by an agent. Owner wallet only.

    Args:
        handle (str): Unique agent handle.
        rec_id (uuid.UUID): Recommendation UUID to retract.
        wallet (AuthedWallet): Wallet proven by the bearer token.
        session (Session): Database session.

    Returns:
        RecommendationResponse: Updated recommendation marked as retracted.
    """
    agent = get_agent_by_handle(session, handle)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    _require_agent_owner(agent, wallet, "retract")
    rec = get_recommendation_by_id(session, rec_id)
    if not rec or rec.agent_id != agent.id:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return retract_recommendation_repo(session, rec)


# ---------------------------------------------------------------------------
# Purchase Requests (agent-scoped)
# ---------------------------------------------------------------------------


@router.post(
    "/{handle}/purchase-requests",
    response_model=PurchaseRequestResponse,
    status_code=201,
    responses=_OWNER_ONLY_RESPONSES,
)
def submit_purchase_request(
    handle: str,
    data: PurchaseRequestCreate,
    wallet: AuthedWallet = Depends(current_wallet),
    session: Session = Depends(get_session),
    _: None = Depends(agent_write_rate_limiter),
):
    """Submit a purchase request on behalf of an agent. Owner wallet only.

    Without this check anyone could file requests in a trusted agent's name.

    Args:
        handle (str): Unique agent handle.
        data (PurchaseRequestCreate): Purchase request payload.
        wallet (AuthedWallet): Wallet proven by the bearer token.
        session (Session): Database session.

    Returns:
        PurchaseRequestResponse: Created purchase request.
    """
    agent = get_agent_by_handle(session, handle)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    _require_agent_owner(agent, wallet, "purchase_request")
    req = create_purchase_request(
        session, agent.id, data.listing_id, data.requester_address, data.reason
    )
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
    reqs, total = list_purchase_requests(
        session, agent_id=agent.id, status=status, offset=offset, limit=limit
    )
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
    reqs, total = list_purchase_requests(
        session, status=status, offset=offset, limit=limit
    )
    return PurchaseRequestListResponse(requests=reqs, count=len(reqs), total=total)


_REVIEW_ERROR_RESPONSES = {
    401: {"model": ErrorResponse, "description": "Missing or invalid bearer token"},
    403: {
        "model": ErrorResponse,
        "description": "Signed-in wallet is not the request's requester_address",
    },
    404: {"description": "Purchase request not found"},
    409: {"model": ErrorResponse, "description": "Request was already reviewed"},
}


@purchase_router.post(
    "/{request_id}/review",
    response_model=PurchaseRequestResponse,
    responses=_REVIEW_ERROR_RESPONSES,
)
def review_purchase_request_route(
    request_id: uuid.UUID,
    data: PurchaseRequestReview,
    wallet: AuthedWallet = Depends(current_wallet),
    session: Session = Depends(get_session),
):
    """Review (approve or reject) a purchase request.

    Requires a user-scope bearer token. Only the wallet named in the request's
    ``requester_address`` (the buyer who would pay) may review it, and only
    while it is pending. ``reviewed_by`` is recorded from the token; any value
    in the body is ignored.

    Args:
        request_id (uuid.UUID): Purchase request UUID.
        data (PurchaseRequestReview): Review decision payload.
        wallet (AuthedWallet): Wallet proven by the bearer token.
        session (Session): Database session.

    Raises:
        ApiError: 401 without a valid token, 403 when the wallet is not the
            requester, 409 when the request is no longer pending.
        HTTPException: 404 when the request does not exist.

    Returns:
        PurchaseRequestResponse: Updated purchase request.
    """
    req = get_purchase_request_by_id(session, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Purchase request not found")
    if not same_evm_address(req.requester_address, wallet.address):
        logger.warning(
            "purchase_requests.review forbidden request_id=%s", request_id
        )
        raise ApiError(
            status_code=403,
            error="forbidden",
            message="Only the requesting wallet can review this purchase request.",
        )
    if req.status != "pending":
        raise ApiError(
            status_code=409,
            error="already_reviewed",
            message="This purchase request has already been reviewed.",
            details={"status": req.status},
        )
    reviewed = review_purchase_request_repo(
        session, req, data.status, wallet.address
    )
    if reviewed is None:
        # Lost a race with a concurrent review of the same request.
        raise ApiError(
            status_code=409,
            error="already_reviewed",
            message="This purchase request has already been reviewed.",
            details={"status": req.status},
        )
    logger.info(
        "purchase_requests.review request_id=%s status=%s", request_id, data.status
    )
    return reviewed


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
    recs, total = list_recommendations(
        session, listing_id=listing_id, offset=offset, limit=limit
    )
    return RecommendationListResponse(
        recommendations=recs, count=len(recs), total=total
    )
