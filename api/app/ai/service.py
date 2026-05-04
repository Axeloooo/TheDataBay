"""Semantic dataset search service."""

from __future__ import annotations

import asyncio
import logging
import uuid as _uuid_mod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from fastapi import Depends

from ..config.settings import Settings, get_settings
from ..contracts.service import get_all_items
from ..llm.dependencies import get_llm_service
from ..llm.service import LLMService
from ..vectorstore.repositories.pgvector_repository import (
    PGVectorRepository,
    pgvector_repository_for_settings,
)
from .schemas import RankedDataset

logger = logging.getLogger(__name__)

_SCORE_HIGH = 0.5
_SCORE_MODERATE = 0.4
_SCORE_LOW = 0.2
_MAX_ROW_FETCH = 200


def _clamp(score: float) -> float:
    return max(0.0, min(1.0, score))


def _score_label(score: float) -> Literal["high", "moderate", "low", "no_match"]:
    if score >= _SCORE_HIGH:
        return "high"
    if score >= _SCORE_MODERATE:
        return "moderate"
    if score >= _SCORE_LOW:
        return "low"
    return "no_match"


def _bytes32_hex_to_uuid(hex_str: str) -> str:
    """Recover a UUID string from the contract's bytes32 hex listing ID."""
    try:
        raw = hex_str.removeprefix("0x")[:32]
        return str(_uuid_mod.UUID(hex=raw))
    except (ValueError, AttributeError):
        return hex_str


class EmbeddingError(Exception):
    """Raised when query embedding or vector retrieval fails."""


class CollectionNotFoundError(Exception):
    """Raised when the pgvector collection has not been populated yet."""


@dataclass(frozen=True)
class _DatasetHit:
    dataset_id: str
    listing_id: str
    score: float
    score_label: Literal["high", "moderate", "low"]
    best_match: str


class _LLMEmbeddingsAdapter:
    """Minimal embeddings adapter for PGVector construction.

    AIService embeds the user query directly through LLMService.  The adapter is
    only passed to PGVectorRepository because LangChain's PGVector constructor
    expects an embeddings object.
    """

    def __init__(self, llm_service: LLMService) -> None:
        self._llm_service = llm_service

    async def aembed_query(self, text: str) -> list[float]:
        return (await self._llm_service.embed_text(text)).vector

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings = []
        for text in texts:
            embeddings.append((await self._llm_service.embed_text(text)).vector)
        return embeddings


class AIService:
    """Ranks marketplace datasets against a natural-language query."""

    def __init__(
        self,
        *,
        llm_service: LLMService,
        vector_repository: PGVectorRepository,
        contract_listing_fetcher: Callable[[Settings], list[Any]],
        settings: Settings,
    ) -> None:
        self._llm_service = llm_service
        self._vector_repository = vector_repository
        self._contract_listing_fetcher = contract_listing_fetcher
        self._settings = settings

    async def rank_datasets(self, query: str, limit: int = 20) -> list[RankedDataset]:
        """Rank datasets by their strongest matching row."""
        final_limit = max(0, min(limit, int(getattr(self._settings, "top_k", limit))))
        if final_limit == 0:
            return []
        row_fetch_k = _row_fetch_limit(self._settings, final_limit)

        logger.info(
            "ai_service.rank_datasets start query_len=%s limit=%s final_limit=%s row_fetch_k=%s",
            len(query),
            limit,
            final_limit,
            row_fetch_k,
        )

        try:
            embedding = await self._llm_service.embed_text(query)
        except Exception as exc:
            logger.error("ai_service.rank_datasets embedding_failed: %s", exc)
            raise EmbeddingError(str(exc)) from exc

        try:
            row_hits = await self._vector_repository.similarity_search_by_vector(
                embedding.vector,
                k=row_fetch_k,
            )
        except ValueError as exc:
            if "Collection not found" in str(exc):
                logger.info("ai_service.rank_datasets collection_not_found")
                raise CollectionNotFoundError(str(exc)) from exc
            logger.error("ai_service.rank_datasets vector_search_failed: %s", exc)
            raise EmbeddingError(str(exc)) from exc
        except Exception as exc:
            logger.error("ai_service.rank_datasets vector_search_failed: %s", exc)
            raise EmbeddingError(str(exc)) from exc

        logger.info(
            "ai_service.rank_datasets raw_hits=%s top_scores=%s min_score=%.3f",
            len(row_hits),
            [round(s, 3) for _, s in row_hits[:5]],
            _minimum_match_score(self._settings),
        )

        dataset_hits = _aggregate_dataset_hits(
            row_hits,
            min_score=_minimum_match_score(self._settings),
        )
        if not dataset_hits:
            logger.info("ai_service.rank_datasets no matching row hits")
            return []

        loop = asyncio.get_running_loop()
        contract_items = await loop.run_in_executor(
            None,
            self._contract_listing_fetcher,
            self._settings,
        )
        item_map = {_bytes32_hex_to_uuid(str(item.id)): item for item in contract_items}
        logger.info(
            "ai_service.rank_datasets dataset_hits=%s contract_items=%s contract_ids=%s",
            len(dataset_hits),
            len(contract_items),
            [_bytes32_hex_to_uuid(str(item.id)) for item in contract_items],
        )

        results: list[RankedDataset] = []
        for hit in dataset_hits:
            item = item_map.get(hit.listing_id)
            if item is None:
                logger.info(
                    "ai_service.rank_datasets stale_hit listing_id=%s (not in contract)",
                    hit.listing_id,
                )
                continue

            results.append(
                RankedDataset(
                    dataset_id=hit.dataset_id,
                    listing_id=hit.listing_id,
                    title=item.title,
                    description=item.description,
                    seller=item.seller,
                    payment_token=item.payment_token,
                    price_atomic=int(item.price_atomic),
                    settlement_currency=item.settlement_currency,
                    settlement_decimals=int(item.settlement_decimals),
                    purchase_count=int(item.purchase_count),
                    score=hit.score,
                    score_label=hit.score_label,
                    best_match=hit.best_match,
                )
            )
            if len(results) >= final_limit:
                break

        logger.info("ai_service.rank_datasets done results=%s", len(results))
        return results


def _aggregate_dataset_hits(
    row_hits: list[tuple[object, float]],
    *,
    min_score: float = _SCORE_LOW,
) -> list[_DatasetHit]:
    best_by_listing: dict[str, _DatasetHit] = {}
    for doc, raw_similarity in row_hits:
        metadata = getattr(doc, "metadata", {}) or {}
        listing_id = metadata.get("listing_id")
        if not listing_id:
            continue

        score = _clamp(float(raw_similarity))
        label = _score_label(score)
        if label == "no_match" or score < min_score:
            continue

        normalized_listing_id = _bytes32_hex_to_uuid(str(listing_id))
        hit = _DatasetHit(
            dataset_id=normalized_listing_id,
            listing_id=normalized_listing_id,
            score=score,
            score_label=label,
            best_match=str(getattr(doc, "page_content", "") or ""),
        )
        current = best_by_listing.get(normalized_listing_id)
        if current is None or hit.score > current.score:
            best_by_listing[normalized_listing_id] = hit

    return sorted(best_by_listing.values(), key=lambda hit: hit.score, reverse=True)


def _row_fetch_limit(_settings: Settings, _final_limit: int) -> int:
    return _MAX_ROW_FETCH


def _minimum_match_score(settings: Settings) -> float:
    configured = getattr(settings, "similarity_threshold", None)
    if configured is None:
        return _SCORE_LOW
    return max(_SCORE_LOW, float(configured))


def get_ai_service(
    settings: Settings = Depends(get_settings),
    llm_service: LLMService = Depends(get_llm_service),
) -> AIService:
    """FastAPI dependency that returns a production AIService instance."""
    return AIService(
        llm_service=llm_service,
        vector_repository=pgvector_repository_for_settings(
            settings,
            embeddings=_LLMEmbeddingsAdapter(llm_service),
        ),
        contract_listing_fetcher=get_all_items,
        settings=settings,
    )
