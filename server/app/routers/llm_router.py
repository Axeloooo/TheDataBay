"""
LLM router for embedding generation using Ollama.
"""

from fastapi import APIRouter, File, UploadFile, BackgroundTasks, status, Depends
from ..schemas.job_schema import JobResponse, JobStatusResponse
from ..schemas.llm_schema import VectorSpec, QueryEmbeddingRequest, QueryEmbeddingResponse
from ..services.llm_service import get_llm_service, LLMService
from ..services.llm_job_service import get_llm_job_service, LLMJobService
from ..config.settings import Settings, get_settings

router = APIRouter(
    prefix="/api/v1/llm",
    tags=["llm"],
)


@router.post(
    "/embed/batch", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED
)
async def create_batch_embeddings(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    llm_job_service: LLMJobService = Depends(get_llm_job_service),
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
        llm_job_service (LLMJobService): Job orchestration service

    Returns:
        JobResponse: Job submission response with job ID
    """
    return await llm_job_service.enqueue_batch_job(file, background_tasks)


@router.post("/embed/query", response_model=QueryEmbeddingResponse)
async def embed_query(
    request: QueryEmbeddingRequest,
    llm_service: LLMService = Depends(get_llm_service),
    settings: Settings = Depends(get_settings),
):
    """Embed a query for retrieval.

    Args:
        request (QueryEmbeddingRequest): Query embedding request
        llm_service (LLMService): LLM service instance
        settings (Settings): Application settings instance

    Returns:
        QueryEmbeddingResponse: Complete response with embedding, and vectorSpec
    """
    query_embedding, dimension = llm_service.generate_single_embedding(request.query)

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
    job_id: str, llm_job_service: LLMJobService = Depends(get_llm_job_service)
):
    """Poll job status and retrieve results.

    Args:
        job_id (str): Job identifier
        llm_job_service (LLMJobService): Job orchestration service

    Returns:
        JobStatusResponse: Job status and result details
    """
    return llm_job_service.get_job_status(job_id)
