"""Generic LLM service interface."""

from typing import Protocol

from .schemas import EmbeddingBatchResult, EmbeddingResult, SummaryResult


class LLMService(Protocol):
    """Interface implemented by concrete LLM providers."""

    async def summarize_text(self, text: str) -> SummaryResult:
        """Generate a structured summary for text."""

    async def embed_text(self, text: str) -> EmbeddingResult:
        """Generate one embedding vector."""

    async def embed_texts(self, texts: list[str]) -> EmbeddingBatchResult:
        """Generate embedding vectors for multiple texts."""
