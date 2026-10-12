"""Generic LLM service interface."""

from typing import Protocol

from .schemas import ColumnExpansionResult, EmbeddingBatchResult, EmbeddingResult


class LLMService(Protocol):
    """Interface implemented by concrete LLM providers."""

    async def expand_column_names(
        self,
        column_names: list[str],
        sample_rows: list[list[str]],
    ) -> ColumnExpansionResult:
        """Return plain-English descriptions for CSV column names.

        Given abbreviated or encoded column names (e.g. chol, cp, sex) and a
        small sample of row values, returns a mapping from each raw column name
        to a human-readable description suitable for use in embedding content.
        Falls back to the raw column name when a description cannot be produced.
        """

    async def embed_text(self, text: str) -> EmbeddingResult:
        """Generate one embedding vector."""

    async def embed_texts(self, texts: list[str]) -> EmbeddingBatchResult:
        """Generate embedding vectors for multiple texts."""
