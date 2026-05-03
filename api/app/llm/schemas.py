"""Pydantic schemas for generic LLM operations."""

from pydantic import BaseModel, Field


class EmbeddingResult(BaseModel):
    """Single embedding vector plus model metadata."""

    vector: list[float]
    model: str
    dimension: int


class EmbeddingBatchResult(BaseModel):
    """Batch embedding result plus model metadata."""

    embeddings: list[EmbeddingResult]
    model: str


class ColumnExpansionResult(BaseModel):
    """Mapping of raw CSV column names to plain-English descriptions."""

    columns: dict[str, str]
