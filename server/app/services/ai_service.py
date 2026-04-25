"""
AI Service for ranking datasets via pgvector semantic search.
"""

import asyncio
import logging
import uuid as _uuid_mod
from typing import Callable, Literal

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.settings import Settings, get_settings
from ..repositories.dataset_embedding_repo import DatasetEmbeddingRepository
from ..schemas.ai_schema import RankedDataset
from ..services.contract_service import get_all_items
from ..services.llm_service import generate_single_embedding

logger = logging.getLogger(__name__)

_SCORE_HIGH = 0.66
_SCORE_MODERATE = 0.33


def _clamp(score: float) -> float:
    return max(0.0, min(1.0, score))


def _score_label(score: float) -> Literal["high", "moderate", "low"]:
    if score > _SCORE_HIGH:
        return "high"
    if score > _SCORE_MODERATE:
        return "moderate"
    return "low"


def _bytes32_hex_to_uuid(hex_str: str) -> str:
    """Recover the original UUID string from a bytes32 hex-encoded item ID.

    The Marketplace contract stores listing IDs as bytes32, where the first
    16 bytes are the UUID and the last 16 bytes are zero-padding
    (see ``contract_service.uuid_to_bytes32``).  ``_item_view_to_schema`` calls
    ``Web3.to_hex()`` on those 32 bytes, producing a string like
    ``"0xa8b3f2c147b34d8e9f3e123456789abc00000000000000000000000000000000"``.
    This helper reverses that encoding so the id can be matched against the
    UUID string stored in ``dataset_embeddings.listing_id``.

    Falls back to returning ``hex_str`` unchanged when the input is already
    a UUID string or cannot be decoded.

    Args:
        hex_str: ``"0x"``-prefixed 64-char hex string (32 bytes).

    Returns:
        UUID-formatted string (e.g. ``"a8b3f2c1-47b3-4d8e-9f3e-123456789abc"``).
    """
    try:
        raw = hex_str.removeprefix("0x")[:32]  # first 16 bytes = 32 hex chars
        return str(_uuid_mod.UUID(hex=raw))
    except (ValueError, AttributeError):
        return hex_str  # passthrough — already UUID or unexpected format


class EmbeddingError(Exception):
    """Raised when query embedding generation fails (e.g. Ollama unavailable)."""


class AIService:
    """Ranks marketplace datasets against a natural-language query via pgvector ANN search."""

    def __init__(
        self,
        embedding_repo: DatasetEmbeddingRepository,
        session_factory: Callable,
        contract_listing_fetcher: Callable,
        embedding_fn: Callable,
        settings: Settings,
    ) -> None:
        self._embedding_repo = embedding_repo
        self._session_factory = session_factory
        self._contract_listing_fetcher = contract_listing_fetcher
        self._embedding_fn = embedding_fn
        self._settings = settings

    async def rank_datasets(self, query: str, limit: int = 20) -> list[RankedDataset]:
        """Rank marketplace datasets by cosine similarity to *query*.

        1. Embeds *query* via Ollama (raises EmbeddingError on failure).
        2. Runs pgvector ANN query via DatasetEmbeddingRepository.
        3. Cross-references results with current on-chain contract items.
        4. Clamps raw scores to [0, 1], derives score_label, applies threshold.

        The join between pgvector results (UUID listing_id) and contract items
        (bytes32 hex id) is normalised via ``_bytes32_hex_to_uuid``.

        Args:
            query: Natural-language search query (must be non-empty).
            limit: Maximum number of results to return (1–20).

        Returns:
            List of RankedDataset ordered by descending similarity score.

        Raises:
            EmbeddingError: When Ollama is unavailable or embedding fails.
        """
        logger.info(
            "ai_service.rank_datasets start query_len=%s limit=%s",
            len(query),
            limit,
        )

        # 1. Generate query embedding.
        #    generate_single_embedding() calls ollama.embed() — blocking I/O.
        #    Offload to a thread so concurrent async requests are not stalled.
        loop = asyncio.get_running_loop()
        try:
            q_vec, _ = await loop.run_in_executor(
                None, self._embedding_fn, query, self._settings
            )
        except Exception as exc:
            logger.error("ai_service.rank_datasets embedding_failed: %s", exc)
            raise EmbeddingError(str(exc)) from exc

        # 2. pgvector ANN search
        async with self._session_factory() as db:
            hits = await self._embedding_repo.search_by_vector(db, q_vec, limit)

        if not hits:
            logger.info("ai_service.rank_datasets no pgvector hits")
            return []

        # 3. Fetch current on-chain items off the event loop (sync Web3 call).
        contract_items = await loop.run_in_executor(
            None, self._contract_listing_fetcher, self._settings
        )

        # Build lookup keyed by UUID string so it matches the listing_id stored
        # in dataset_embeddings (the contract returns bytes32 hex; normalise it).
        item_map = {_bytes32_hex_to_uuid(item.id): item for item in contract_items}

        # 4. Join, clamp, filter, label
        results: list[RankedDataset] = []
        for listing_id, raw_score in hits:
            item = item_map.get(listing_id)
            if item is None:
                # Stale pgvector hit — listing no longer on-chain
                logger.debug("ai_service.rank_datasets stale_hit listing_id=%s", listing_id)
                continue

            score = _clamp(raw_score)

            if (
                self._settings.similarity_threshold is not None
                and score < self._settings.similarity_threshold
            ):
                continue

            results.append(
                RankedDataset(
                    listing_id=listing_id,
                    title=item.title,
                    description=item.description,
                    seller=item.seller,
                    payment_token=item.payment_token,
                    price_atomic=int(item.price_atomic),
                    settlement_currency=item.settlement_currency,
                    settlement_decimals=int(item.settlement_decimals),
                    purchase_count=int(item.purchase_count),
                    score=score,
                    score_label=_score_label(score),
                )
            )

        logger.info("ai_service.rank_datasets done results=%s", len(results))
        return results


def get_ai_service(
    settings: Settings = Depends(get_settings),
) -> AIService:
    """FastAPI dependency that returns a production AIService instance.

    The session factory is wrapped in a closure so the async engine is
    created lazily — avoiding import-time engine initialisation in test
    environments that use a non-async driver.

    Args:
        settings: Application settings (injected by FastAPI).

    Returns:
        AIService wired with production dependencies.
    """
    from ..database.async_engine import get_async_session_factory

    def _session_factory() -> AsyncSession:
        return get_async_session_factory()()

    return AIService(
        embedding_repo=DatasetEmbeddingRepository(),
        session_factory=_session_factory,
        contract_listing_fetcher=get_all_items,
        embedding_fn=generate_single_embedding,
        settings=settings,
    )
