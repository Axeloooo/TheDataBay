"""
Pydantic schemas for LLM endpoints.
"""

from pydantic import BaseModel, Field
from typing import List


class EmbeddingRequest(BaseModel):
    """Request model for single embedding.

    Args:
        BaseModel (BaseModel): Pydantic BaseModel
    """

    text: str = Field(..., description="Text to embed", min_length=1)


class EmbeddingResponse(BaseModel):
    """Response model for embedding.

    Args:
        BaseModel (BaseModel): Pydantic BaseModel
    """

    embedding: List[float] = Field(..., description="Generated embedding vector")
    model: str = Field(..., description="Model used for embedding")


class BatchEmbeddingFileResponse(BaseModel):
    """Response model for batch embeddings from file upload.

    Args:
        BaseModel (BaseModel): Pydantic BaseModel
    """

    embeddings: List[List[float]] = Field(..., description="List of embedding vectors")
    model: str = Field(..., description="Model used for embedding")
    count: int = Field(..., description="Number of embeddings generated")
    filename: str = Field(..., description="Name of the uploaded file")
    rows_processed: int = Field(..., description="Number of rows processed from file")


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
