"""
AI router for similarity search and ML workflows.
"""

import logging
import time
from typing import List
from fastapi import APIRouter, Depends

from ..services.contract_service import get_all_items
from ..config.settings import Settings, get_settings

from ..schemas.marketplace_schema import MarketplaceDataItem
from ..schemas.ai_schema import (
    RankedDataset,
    SimilaritySearchRequest,
    SimilaritySearchResponse,
)
from ..services.ai_service import get_ai_service, AIService

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])
logger = logging.getLogger(__name__)


@router.post("/similarity-search", response_model=SimilaritySearchResponse)
async def similarity_search(
    request: SimilaritySearchRequest,
    ai_service: AIService = Depends(get_ai_service),
    settings: Settings = Depends(get_settings),
):
    """Perform similarity search over marketplace datasets based on query embedding.

    Args:
        request (SimilaritySearchRequest): Similarity search request model
        ai_service (AIService, optional): AI service instance. Defaults to Depends(get_ai_service).
        settings (Settings, optional): Settings instance. Defaults to Depends(get_settings).

    Returns:
        SimilaritySearchResponse: Response containing ranked datasets based on similarity search
    """

    started = time.perf_counter()
    logger.info("ai.similarity_search called query_len=%s", len(request.query))
    datasets: List[MarketplaceDataItem] = get_all_items(settings)
    if not datasets:
        logger.info("ai.similarity_search no datasets")
        return SimilaritySearchResponse(query=request.query, results=[], count=0)

    ranked: List[RankedDataset] = await ai_service.rank_datasets(
        query=request.query,
        datasets=datasets,
    )

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    logger.info(
        "ai.similarity_search completed query_len=%s candidates=%s results=%s elapsed_ms=%s",
        len(request.query),
        len(datasets),
        len(ranked),
        elapsed_ms,
    )
    return SimilaritySearchResponse(
        query=request.query,
        results=ranked,
        count=len(ranked),
    )
