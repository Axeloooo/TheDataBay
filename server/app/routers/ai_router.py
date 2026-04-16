"""
AI router for similarity search.
"""

import logging
import time
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from ..schemas.ai_schema import (
    ErrorResponse,
    SimilaritySearchRequest,
    SimilaritySearchResponse,
)
from ..services.ai_service import AIService, EmbeddingError, get_ai_service

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])
logger = logging.getLogger(__name__)


@router.post(
    "/similarity-search",
    response_model=SimilaritySearchResponse,
    responses={
        422: {"model": ErrorResponse, "description": "Validation error"},
        503: {"model": ErrorResponse, "description": "Embedding service unavailable"},
    },
)
async def similarity_search(
    request: SimilaritySearchRequest,
    ai_service: AIService = Depends(get_ai_service),
):
    """Rank marketplace datasets by semantic similarity to a natural-language query.

    Args:
        request: Query string and optional result limit.
        ai_service: Injected AIService instance.

    Returns:
        SimilaritySearchResponse: Ordered list of matching datasets with scores.

    Raises:
        HTTPException 503: When Ollama query-embedding is unavailable.
    """
    started = time.perf_counter()
    logger.info(
        "ai.similarity_search called query_len=%s limit=%s",
        len(request.query),
        request.limit,
    )

    try:
        ranked = await ai_service.rank_datasets(request.query, request.limit)
    except EmbeddingError as exc:
        return JSONResponse(
            status_code=503,
            content=ErrorResponse(
                error="embedding_unavailable",
                message="Query embedding generation failed; Ollama may be unavailable.",
                details={"cause": str(exc)},
            ).model_dump(),
        )

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    logger.info(
        "ai.similarity_search completed results=%s elapsed_ms=%s",
        len(ranked),
        elapsed_ms,
    )
    return SimilaritySearchResponse(
        query=request.query,
        results=ranked,
        count=len(ranked),
    )
