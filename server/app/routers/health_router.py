"""
Health check router for service status and readiness endpoints.
"""

from fastapi import APIRouter
from ..schemas.health_schema import HealthResponse, ReadinessResponse
from ..config import settings

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

    return HealthResponse(
        status="healthy", version=settings.app_version, service=settings.app_name
    )


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check():
    """Readiness check endpoint. Can be extended to check dependencies (database, ollama, etc.)

    Returns:
        ReadinessResponse: Readiness response model
    """

    dependencies = {"ollama": "available", "database": "not_configured"}

    return ReadinessResponse(ready=True, dependencies=dependencies)
