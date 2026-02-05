"""
LLM router for embedding generation using Ollama.
"""

from fastapi import APIRouter, File, UploadFile, BackgroundTasks, status, Depends
from ..schemas.job_schema import JobResponse, JobStatusResponse
from ..schemas.llm_schema import VectorSpec, QueryEmbeddingRequest, QueryEmbeddingResponse
from ..services.job_manager import JobManager, get_job_manager
from ..services.llm_job_service import enqueue_batch_job, get_job_status as get_job_status_service
from ..services.llm_service import generate_single_embedding
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
        settings (Settings): Application settings instance
        job_manager (JobManager): Job manager instance

    Returns:
        JobResponse: Job submission response with job ID
    """
    return await enqueue_batch_job(
        file=file,
        background_tasks=background_tasks,
        settings=settings,
        job_manager=job_manager,
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
    query_embedding, dimension = generate_single_embedding(request.query, settings)

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
    return get_job_status_service(job_id, job_manager)
