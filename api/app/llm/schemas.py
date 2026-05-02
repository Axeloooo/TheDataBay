"""Pydantic schemas for generic LLM operations."""

from pydantic import BaseModel, ConfigDict, Field


class TextSummary(BaseModel):
    """Strict JSON schema expected from summary models."""

    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    keywords: list[str] = Field(min_length=1)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)


class SummaryResult(BaseModel):
    """Validated summary plus model metadata."""

    summary: TextSummary
    model: str


class EmbeddingResult(BaseModel):
    """Single embedding vector plus model metadata."""

    vector: list[float]
    model: str
    dimension: int


class EmbeddingBatchResult(BaseModel):
    """Batch embedding result plus model metadata."""

    embeddings: list[EmbeddingResult]
    model: str
