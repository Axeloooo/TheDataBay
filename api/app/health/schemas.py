"""
Pydantic schemas for health endpoints.
"""

from pydantic import BaseModel, Field
from typing import Dict, Optional


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str = Field(..., description="Service health status")
    version: str = Field(..., description="API version")
    service: str = Field(..., description="Service name")


class ReadinessResponse(BaseModel):
    """Response model for readiness check endpoint."""

    ready: bool = Field(..., description="Whether the service is ready")
    dependencies: Dict[str, str] = Field(
        default_factory=dict, description="Status of dependencies"
    )
    indexer_lag_blocks: Optional[int] = Field(
        default=None,
        description=(
            "Blocks between the chain head and the last indexed block, as of "
            "the indexer's last run. Null when the indexer is disabled or has "
            "not completed a run."
        ),
    )
