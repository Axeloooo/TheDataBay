"""
Pydantic schemas for AI endpoints.
"""

from pydantic import BaseModel, Field
from typing import List

from ..schemas.marketplace_schema import MarketplaceDataItem


class SimilaritySearchRequest(BaseModel):
    """Request model for similarity search."""

    query: str = Field(..., description="Search query")


class ScoreExplanation(BaseModel):
    """Explanation of the scoring method used."""

    method: str = "topk_mean_cosine"
    k_rows: int
    rows_in_dataset: int
    dimension: int
    normalized: bool = True


class RankedDataset(BaseModel):
    """Ranked dataset item with score and explanation."""

    item: MarketplaceDataItem
    score: float = Field(..., ge=-1.0, le=1.0)
    explanation: ScoreExplanation


class SimilaritySearchResponse(BaseModel):
    """Response model for similarity search."""

    query: str = Field(..., description="Search query")
    results: List[RankedDataset] = Field(..., description="Search results")
    count: int = Field(..., description="Number of results returned")
