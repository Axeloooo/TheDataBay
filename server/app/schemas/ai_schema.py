"""
Pydantic schemas for AI endpoints.
"""

from typing import Literal
from pydantic import BaseModel, Field


class SimilaritySearchRequest(BaseModel):
    """Request model for similarity search."""

    query: str = Field(..., min_length=1, description="Search query")
    limit: int = Field(default=20, ge=1, le=20, description="Maximum results to return (1–20)")


class RankedDataset(BaseModel):
    """Flat ranked dataset item with normalised cosine similarity score."""

    listing_id: str
    title: str
    description: str
    seller: str
    price_atomic: int
    score: float = Field(..., ge=0.0, le=1.0, description="Cosine similarity (0.0–1.0)")
    score_label: Literal["high", "moderate", "low"]


class SimilaritySearchResponse(BaseModel):
    """Response model for similarity search."""

    query: str = Field(..., description="Search query")
    results: list[RankedDataset] = Field(..., description="Ranked search results")
    count: int = Field(..., description="Number of results returned")


class ErrorResponse(BaseModel):
    """Standardised error response shape."""

    error: str
    message: str
    details: dict | None = None
