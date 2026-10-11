"""
Health check router for service status and readiness endpoints.
"""

import logging

from fastapi import APIRouter
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from .schemas import HealthResponse, ReadinessResponse
from ..config.settings import Settings, get_settings
from ..database import engine as db_engine
from ..indexer.models import IndexerState
from ..indexer.service import STATE_NAME, is_stale

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/health",
    tags=["health"],
)


@router.get("/", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint.

    Returns:
        HealthResponse: Health response model
    """
    settings = get_settings()
    return HealthResponse(
        status="healthy", version=settings.app_version, service=settings.app_name
    )


def _indexer_status(settings: Settings) -> tuple[str, int | None]:
    """Indexer status and lag in blocks, read from the indexer cursor only.

    Status is one of disabled, unavailable, starting, stale, catching_up, synced.
    """
    if not settings.indexer_enabled:
        return "disabled", None
    try:
        with Session(db_engine.get_engine()) as session:
            state = session.get(IndexerState, STATE_NAME)
    except SQLAlchemyError:
        logger.exception("Readiness: failed to read indexer state")
        return "unavailable", None
    if state is None or state.chain_head_block is None:
        return "starting", None
    lag = max(state.chain_head_block - state.last_indexed_block, 0)
    if is_stale(state, settings):
        # Lag is as of the last tick, which is too old to trust.
        return "stale", lag
    return ("synced" if lag <= settings.indexer_confirmations else "catching_up"), lag


@router.get("/ready", response_model=ReadinessResponse)
def readiness_check():
    """Readiness check endpoint. Can be extended to check dependencies (database, ollama, etc.)

    Indexer lag is informational: it never marks the pod unready, so a slow
    RPC provider cannot take the API out of rotation.

    Returns:
        ReadinessResponse: Readiness response model
    """
    settings = get_settings()
    indexer_status, indexer_lag = _indexer_status(settings)
    dependencies = {
        "ollama": "available",
        "database": "not_configured",
        "indexer": indexer_status,
    }

    return ReadinessResponse(
        ready=True, dependencies=dependencies, indexer_lag_blocks=indexer_lag
    )
