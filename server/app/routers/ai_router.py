"""
AI router for similarity search and ML workflows.
"""

from typing import List
from fastapi import APIRouter
from fastapi.params import Depends

from ..services.marketplace_service import get_marketplace_items
from ..config.settings import Settings, get_settings

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

    # TODO: Test whole flow with deployed smart contract

    datasets: List[MarketplaceDataItem] = await get_marketplace_items(settings)
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
