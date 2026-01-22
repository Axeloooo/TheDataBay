"""
AI router for similarity search and ML workflows.
"""

from typing import List
from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from ..schemas.ai_schema import (
    DataItem,
    SimilaritySearchRequest,
    SimilaritySearchResponse,
    SimilarityResult,
)
from ..services.ai_service import get_ai_service, AIService

router = APIRouter(prefix="/ai", tags=["ai"])


async def get_marketplace_datasets() -> List[DataItem]:
    return [
        DataItem(
            id="dataset1",
            title="Sample Dataset 1",
            description="This is a sample dataset for testing.",
            seller="0xSellerAddress1",
            price_usd=9.99,
            dataset_url="ipfs://QmExampleHashDataset1",
            dataset_hash="0xExampleDatasetHash1",
            signature_url="ipfs://QmExampleHash1",
            signature_hash="0xExampleHash1",
            exists=True,
            access_list={"0xBuyerAddress1": True},
        ),
    ]


@router.post("/similarity-search", response_model=SimilaritySearchResponse)
async def similarity_search(
    request: SimilaritySearchRequest, ai_service: AIService = Depends(get_ai_service)
):
    datasets: List[DataItem] = await get_marketplace_datasets()
    if not datasets:
        raise HTTPException(status_code=404, detail="No datasets available to search")

    ranked: List[SimilarityResult] = await ai_service.rank_datasets(
        query=request.query,
        datasets=datasets,
        top_k=request.top_k,
        threshold=request.threshold,
        k_rows=100,
    )

    return SimilaritySearchResponse(
        query=request.query,
        results=ranked,
        count=len(ranked),
    )
