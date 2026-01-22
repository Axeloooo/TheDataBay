"""
AI router for similarity search and ML workflows.
"""

from typing import List
from fastapi import APIRouter
from fastapi.params import Depends

from ..services.marketplace_service import MarketplaceService, get_marketplace_service

from ..schemas.marketplace_schema import MarketplaceDataItem
from ..schemas.ai_schema import (
    RankedDataset,
    SimilaritySearchRequest,
    SimilaritySearchResponse,
)
from ..services.ai_service import get_ai_service, AIService

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/similarity-search", response_model=SimilaritySearchResponse)
async def similarity_search(
    request: SimilaritySearchRequest,
    ai_service: AIService = Depends(get_ai_service),
    marketplace_service: MarketplaceService = Depends(get_marketplace_service),
):
    """Perform similarity search over marketplace datasets based on query embedding.

    Args:
        request (SimilaritySearchRequest): Similarity search request model
        ai_service (AIService, optional): AI service instance. Defaults to Depends(get_ai_service).
        marketplace_service (MarketplaceService, optional): Marketplace service instance. Defaults to Depends(get_marketplace_service).

    Returns:
        SimilaritySearchResponse: Response containing ranked datasets based on similarity search
    """
    datasets: List[MarketplaceDataItem] = (
        await marketplace_service.get_marketplace_items()
    )
    if not datasets:
        return SimilaritySearchResponse(query=request.query, results=[], count=0)

    ranked: List[RankedDataset] = await ai_service.rank_datasets(
        query=request.query,
        datasets=datasets,
    )

    return SimilaritySearchResponse(
        query=request.query,
        results=ranked,
        count=len(ranked),
    )
