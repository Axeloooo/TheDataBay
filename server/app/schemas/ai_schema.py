"""
Pydantic schemas for AI endpoints.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any


class SimilaritySearchRequest(BaseModel):
    """Request model for similarity search."""

    query: str = Field(..., description="Search query", min_length=1)
    top_k: int = Field(
        default=10, description="Number of results to return", ge=1, le=100
    )
    threshold: float | None = Field(
        None, description="Similarity threshold", ge=0.0, le=1.0
    )


class SimilarityResult(BaseModel):
    """Individual similarity search result."""

    id: str = Field(..., description="Result identifier")
    score: float = Field(..., description="Similarity score", ge=0.0, le=1.0)
    content: str = Field(..., description="Result content")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class SimilaritySearchResponse(BaseModel):
    """Response model for similarity search."""

    query: str = Field(..., description="Original query")
    results: List[SimilarityResult] = Field(
        default_factory=list, description="Search results"
    )
    count: int = Field(..., description="Number of results returned")


class ScoreRequest(BaseModel):
    """Request model for ML scoring."""

    data: Dict[str, Any] = Field(..., description="Data to score")
    model_name: str | None = Field(None, description="Specific model to use")


class ScoreResponse(BaseModel):
    """Response model for ML scoring."""

    score: float = Field(..., description="Computed score")
    confidence: float = Field(..., description="Confidence level", ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional scoring metadata"
    )
