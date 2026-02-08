"""
Pydantic schemas for LLM endpoints.
"""

from pydantic import BaseModel, Field
from typing import List


class VectorSpec(BaseModel):
    """Vector specification metadata."""

    model: str = Field(..., description="Embedding model name")
    dimension: int = Field(..., description="Embedding vector dimension")


class DatasetStats(BaseModel):
    """Dataset statistics."""

    total_rows: int = Field(..., description="Total number of rows in dataset")
    total_columns: int = Field(..., description="Total number of columns in dataset")
    empty_rows_skipped: int = Field(
        default=0, description="Number of empty rows skipped"
    )
    has_header: bool = Field(..., description="Whether dataset has header row")


class DatasetEmbeddingResponse(BaseModel):
    """Response model for dataset embedding with full metadata."""

    signature: List[List[float]] = Field(
        ..., description="Embedding vectors - one per record [n_rows][dimension]"
    )
    vectorSpec: VectorSpec = Field(..., description="Vector specification metadata")
    stats: DatasetStats = Field(..., description="Dataset statistics")
    filename: str = Field(..., description="Original filename")


class QueryEmbeddingRequest(BaseModel):
    """Request model for query embedding."""

    query: str = Field(..., description="Original query", min_length=1)


class QueryEmbeddingResponse(BaseModel):
    """Response model for query embedding."""

    original_query: str = Field(..., description="Original user query")
    query_embedding: List[float] = Field(..., description="Embedding of the query")
    vector_spec: VectorSpec = Field(
        ..., description="Vector specification - compatible with dataset embeddings"
    )


class SignatureInfo(BaseModel):
    """Information about uploaded signature file."""

    signature_url: str = Field(..., description="IPFS URL of the signature file")
    signature_hash: str = Field(
        ..., description="SHA-256 hash of the signature file (0x-prefixed)"
    )
