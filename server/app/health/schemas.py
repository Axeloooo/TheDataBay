"""
Pydantic schemas for health endpoints.
"""

from pydantic import BaseModel, Field
from typing import Dict


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
