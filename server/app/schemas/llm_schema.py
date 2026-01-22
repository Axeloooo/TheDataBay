"""
Pydantic schemas for LLM endpoints.
"""

import datetime
from enum import Enum
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


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
    """Request model for query embedding with rewriting."""

    query: str = Field(..., description="Original query", min_length=1)
    context: str | None = Field(None, description="Optional context for rewriting")


class QueryEmbeddingResponse(BaseModel):
    """Response model for query embedding."""

    original_query: str = Field(..., description="Original user query")
    query_embedding: List[float] = Field(..., description="Embedding of the query")
    vectorSpec: VectorSpec = Field(
        ..., description="Vector specification - compatible with dataset embeddings"
    )


class SignatureInfo(BaseModel):
    """Information about uploaded signature file."""

    signature_url: str = Field(..., description="IPFS URL of the signature file")
    signature_hash: str = Field(
        ..., description="SHA-256 hash of the signature file (0x-prefixed)"
    )


class JobResponse(BaseModel):
    """Response model for job submission."""

    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Job status (queued)")


class JobStatusResponse(BaseModel):
    """Response model for job status polling."""

    job_id: str = Field(..., description="Job identifier")
    status: str = Field(
        ..., description="Job status (queued, running, completed, failed)"
    )
    created_at: str = Field(..., description="Job creation timestamp")
    started_at: Optional[str] = Field(None, description="Job start timestamp")
    completed_at: Optional[str] = Field(None, description="Job completion timestamp")
    error: Optional[str] = Field(None, description="Error message if failed")
    vector_spec: Optional[VectorSpec] = Field(
        None, description="Vector specification (when completed)"
    )
    stats: Optional[DatasetStats] = Field(
        None, description="Dataset statistics (when completed)"
    )
    signature: Optional[SignatureInfo] = Field(
        None, description="Signature file info (when completed)"
    )
    filename: str = Field(..., description="Original filename")


class JobStatus(str, Enum):
    """Job status enumeration."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Job(BaseModel):
    """Job data structure."""

    job_id: str
    status: JobStatus
    filename: str
    created_at: datetime.datetime
    started_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
