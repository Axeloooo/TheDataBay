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


class DataItem(BaseModel):
    """Schema for a single data item."""

    id: str = Field(..., description="Unique identifier for the data item")
    title: str = Field(..., description="Title of the data item")
    description: str = Field(..., description="Description of the data item")
    seller: str = Field(..., description="Seller address")
    price: float = Field(..., description="Price in USD", ge=0.0)
    dataset_url: str = Field(..., description="URL to the dataset")
    dataset_hash: str = Field(
        ..., description="Hash of the dataset for integrity verification"
    )
    signature_url: str = Field(..., description="URL to the signature embeddings")
    signature_hash: str = Field(
        ..., description="Hash of the signature embeddings for integrity verification"
    )
    exists: bool = Field(
        ..., description="Indicates if the item exists in the marketplace"
    )
    access_list: Dict[str, bool] = Field(
        default_factory=dict, description="Mapping of user addresses to access rights"
    )
