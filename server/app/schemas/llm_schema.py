"""
Pydantic schemas for LLM endpoints.
"""

from pydantic import BaseModel, Field
from typing import List


class VectorSpec(BaseModel):
    """Vector specification metadata.

    Args:
        BaseModel (BaseModel): Pydantic BaseModel
    """

    model: str = Field(..., description="Embedding model name")
    dimension: int = Field(..., description="Embedding vector dimension")


class DatasetStats(BaseModel):
    """Dataset statistics.

    Args:
        BaseModel (BaseModel): Pydantic BaseModel
    """

    total_rows: int = Field(..., description="Total number of rows in dataset")
    total_columns: int = Field(..., description="Total number of columns in dataset")
    empty_rows_skipped: int = Field(
        default=0, description="Number of empty rows skipped"
    )
    has_header: bool = Field(..., description="Whether dataset has header row")


class DatasetEmbeddingResponse(BaseModel):
    """Response model for dataset embedding with full metadata.

    Args:
        BaseModel (BaseModel): Pydantic BaseModel
    """

    signature: List[List[float]] = Field(
        ..., description="Embedding vectors - one per record [n_rows][dimension]"
    )
    vectorSpec: VectorSpec = Field(..., description="Vector specification metadata")
    stats: DatasetStats = Field(..., description="Dataset statistics")
    filename: str = Field(..., description="Original filename")


class QueryRewriteRequest(BaseModel):
    """Request model for query rewriting.

    Args:
        BaseModel (BaseModel): Pydantic BaseModel
    """

    query: str = Field(..., description="Original query to rewrite", min_length=1)
    context: str | None = Field(None, description="Optional context for rewriting")


class QueryRewriteResponse(BaseModel):
    """Response model for query rewriting.

    Args:
        BaseModel (BaseModel): Pydantic BaseModel
    """

    original_query: str = Field(..., description="Original query")
    rewritten_query: str = Field(..., description="Rewritten query")
    model: str = Field(..., description="Model used for rewriting")


class QueryEmbeddingRequest(BaseModel):
    """Request model for query embedding with rewriting.

    Args:
        BaseModel (BaseModel): Pydantic BaseModel
    """

    query: str = Field(..., description="Original query", min_length=1)
    context: str | None = Field(None, description="Optional context for rewriting")


class QueryEmbeddingResponse(BaseModel):
    """Response model for query embedding with rewriting.

    Args:
        BaseModel (BaseModel): Pydantic BaseModel
    """

    original_query: str = Field(..., description="Original user query")
    rewritten_query: str = Field(..., description="Rewritten retrieval-friendly query")
    query_embedding: List[float] = Field(
        ..., description="Embedding of the rewritten query"
    )
    vectorSpec: VectorSpec = Field(
        ..., description="Vector specification - compatible with dataset embeddings"
    )
    rewrite_model: str = Field(..., description="Model used for query rewriting")
