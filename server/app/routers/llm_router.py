"""
LLM router for embedding generation using Ollama.
"""

import logging
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)

from ..schemas.job_schema import JobResponse, JobStatusResponse
from ..schemas.marketplace_schema import TOKEN_DECIMALS
from ..schemas.llm_schema import (
    VectorSpec,
    QueryEmbeddingRequest,
    QueryEmbeddingResponse,
)
from ..services.job_manager import JobManager, get_job_manager
from ..services.llm_job_service import (
    enqueue_batch_job,
    get_job_status as get_job_status_service,
)
from ..services.llm_service import embed_query as embed_query_service
from ..config.settings import Settings, get_settings

router = APIRouter(
    prefix="/api/v1/llm",
    tags=["llm"],
)
logger = logging.getLogger(__name__)


@router.post(
    "/embed/batch", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED
)
async def create_batch_embeddings(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(...),
    seller: str = Form(...),
    price: int | None = Form(None),
    price_atomic: int | None = Form(None),
    settlement_currency: str = Form("USDC"),
    settlement_decimals: int = Form(6),
    seller_wallet_type: str = Form("evm"),
    settings: Settings = Depends(get_settings),
    job_manager: JobManager = Depends(get_job_manager),
):
    """Submit a dataset for batch embedding (async job-based).

    Returns immediately with a job ID. The actual embedding work
    runs in the background. Poll GET /llm/jobs/{jobId} for status.

    Validates:
    - File size (max 50MB)
    - File format (.csv only)
    - Row count (max 50,000 rows)

    Args:
        background_tasks (BackgroundTasks): FastAPI background tasks
        file (UploadFile): Dataset file upload
        title (str): Dataset title
        description (str): Dataset description
        seller (str): Seller EVM address
        price (int | None): Legacy price field in settlement token atomic units
        price_atomic (int | None): Preferred price field in settlement token atomic units
        settlement_currency (str): Settlement currency metadata
        settlement_decimals (int): Settlement decimals metadata
        seller_wallet_type (str): Seller wallet type (evm only for now)
        settings (Settings): Application settings instance
        job_manager (JobManager): Job manager instance

    Returns:
        JobResponse: Job submission response with job ID
    """

    logger.info(
        "llm.create_batch_embeddings called filename=%s seller=%s",
        file.filename,
        seller,
    )
    effective_price = price_atomic if price_atomic is not None else price
    if effective_price is None:
        raise HTTPException(status_code=400, detail="price_atomic is required.")
    if settlement_currency not in TOKEN_DECIMALS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported settlement_currency {settlement_currency!r}. "
                f"Supported: {sorted(TOKEN_DECIMALS.keys())}."
            ),
        )
    expected_decimals = TOKEN_DECIMALS[settlement_currency]
    if settlement_decimals != expected_decimals:
        raise HTTPException(
            status_code=400,
            detail=f"settlement_decimals must equal {expected_decimals} for {settlement_currency}.",
        )

    return await enqueue_batch_job(
        file=file,
        background_tasks=background_tasks,
        settings=settings,
        job_manager=job_manager,
        title=title,
        description=description,
        seller=seller,
        price=effective_price,
        seller_wallet_type=seller_wallet_type,
    )


@router.post("/embed/query", response_model=QueryEmbeddingResponse)
async def embed_query(
    request: QueryEmbeddingRequest,
    settings: Settings = Depends(get_settings),
):
    """Embed a query for retrieval.

    Args:
        request (QueryEmbeddingRequest): Query embedding request
        settings (Settings): Application settings instance

    Returns:
        QueryEmbeddingResponse: Complete response with embedding, and vectorSpec
    """
    logger.info("llm.embed_query called query_len=%s", len(request.query))
    query_embedding, dimension = await embed_query_service(request.query, settings)

    vector_spec = VectorSpec(
        model=settings.embedding_model,
        dimension=dimension,
    )

    return QueryEmbeddingResponse(
        original_query=request.query,
        query_embedding=query_embedding,
        vector_spec=vector_spec,
    )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str, job_manager: JobManager = Depends(get_job_manager)
):
    """Poll job status and retrieve results.

    Args:
        job_id (str): Job identifier
        job_manager (JobManager): Job manager instance

    Returns:
        JobStatusResponse: Job status and result details
    """
    logger.info("llm.get_job_status called job_id=%s", job_id)
    return get_job_status_service(job_id, job_manager)
