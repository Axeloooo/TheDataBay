"""
Pydantic schemas for async job endpoints.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from .llm_schema import DatasetStats, SignatureInfo, VectorSpec


class JobResponse(BaseModel):
    """Response model for job submission."""

    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Job status (queued)")
    listing_id: str = Field(..., description="Listing UUID identifier")


class JobStatusResponse(BaseModel):
    """Response model for job status polling."""

    job_id: str = Field(..., description="Job identifier")
    status: str = Field(
        ..., description="Job status (queued, running, completed, failed)"
    )
    listing_id: Optional[str] = Field(
        None, description="Listing UUID identifier (server-generated)"
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
    dataset_url: Optional[str] = Field(
        None, description="Encrypted dataset IPFS URL (when completed)"
    )
    dataset_hash: Optional[str] = Field(
        None, description="Encrypted dataset SHA-256 hash (when completed)"
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
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(validate_assignment=True)
