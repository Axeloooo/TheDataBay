"""
AI router for similarity search.
"""

import logging
import time
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from .schemas import (
    QueryEmbeddingRequest,
    QueryEmbeddingResponse,
    SimilaritySearchRequest,
    SimilaritySearchResponse,
    VectorSpec,
)
from ..shared.errors import ErrorResponse
from .service import (
    AIService,
    CollectionNotFoundError,
    EmbeddingError,
    embed_query,
    get_ai_service,
)
from ..config.settings import Settings, get_settings

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])
logger = logging.getLogger(__name__)


@router.post(
    "/similarity-search",
    response_model=SimilaritySearchResponse,
    responses={
        422: {"model": ErrorResponse, "description": "Validation error"},
        404: {"model": ErrorResponse, "description": "No datasets have been indexed yet"},
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
        HTTPException 404: When no datasets have been indexed yet.
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
    except CollectionNotFoundError:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error="no_datasets_indexed",
                message="No datasets have been indexed yet. Upload a dataset to enable search.",
                details={},
            ).model_dump(),
        )
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


@router.post("/embed/query", response_model=QueryEmbeddingResponse)
async def embed_query_route(
    request: QueryEmbeddingRequest,
    settings: Settings = Depends(get_settings),
):
    """Embed a query for retrieval."""
    logger.info("ai.embed_query called query_len=%s", len(request.query))
    query_embedding, dimension = await embed_query(request.query, settings)
    return QueryEmbeddingResponse(
        original_query=request.query,
        query_embedding=query_embedding,
        vector_spec=VectorSpec(model=settings.embedding_model, dimension=dimension),
    )
