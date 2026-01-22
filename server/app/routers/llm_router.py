"""
LLM router for query rewriting and embedding generation using Ollama.
"""

from fastapi import (
    APIRouter,
    File,
    UploadFile,
    HTTPException,
    BackgroundTasks,
    status,
    Depends,
)
from ..schemas.llm_schema import (
    JobResponse,
    JobStatusResponse,
    VectorSpec,
    DatasetStats,
    SignatureInfo,
    QueryEmbeddingRequest,
    QueryEmbeddingResponse,
)
from ..services.llm_service import get_llm_service, LLMService
from ..services.job_manager import get_job_manager, JobManager, JobStatus
from ..services.pinata_service import get_pinata_service, PinataService
from ..config.settings import get_settings
import csv

router = APIRouter(
    prefix="/llm",
    tags=["llm"],
)


async def process_embedding_job(
    job_id: str,
    content: str,
    filename: str,
    pinata_service: PinataService,
    job_manager: JobManager,
    llm_service: LLMService,
):
    """Background task to process embedding job.

    Args:
        job_id (str): Job identifier
        content (str): File content
        filename (str): Original filename
        pinata_service (PinataService): Pinata service instance
        job_manager (JobManager): Job manager instance
        llm_service (LLMService): LLM service instance
    """
    try:
        # Update job status to running
        job_manager.update_status(job_id, JobStatus.RUNNING)

        # Parse dataset
        data_rows, column_names, has_header, empty_rows_skipped = (
            llm_service.parse_dataset_file(content, filename)
        )

        # Transform to text
        texts = []
        for row in data_rows:
            text = llm_service.record_to_text(row, column_names)
            texts.append(text)

        # Generate embeddings with chunking
        embeddings, dimension = await llm_service.generate_embeddings_chunked(texts)

        # Upload to IPFS
        ipfs_url, signature_hash = await pinata_service.upload_signature(
            embeddings, filename, compress=True
        )

        # Build result
        settings = get_settings()
        result = {
            "vectorSpec": {"model": settings.embedding_model, "dimension": dimension},
            "stats": {
                "total_rows": len(data_rows),
                "total_columns": len(column_names),
                "empty_rows_skipped": empty_rows_skipped,
                "has_header": has_header,
            },
            "signature": {"signature_url": ipfs_url, "signature_hash": signature_hash},
        }

        # Mark job as completed
        job_manager.set_result(job_id, result)
        job_manager.update_status(job_id, JobStatus.COMPLETED)

    except Exception as e:
        # Mark job as failed
        error_msg = str(e)
        job_manager.set_error(job_id, error_msg)


@router.post(
    "/embed/batch", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED
)
async def create_batch_embeddings(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    pinata_service: PinataService = Depends(get_pinata_service),
    job_manager: JobManager = Depends(get_job_manager),
    llm_service: LLMService = Depends(get_llm_service),
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

    Returns:
        JobResponse: Job submission response with job ID
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    file_extension = file.filename.split(".")[-1].lower()
    if file_extension not in ["csv"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: .{file_extension}. Only .csv files are supported.",
        )

    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")

    settings = get_settings()
    file_size_mb = len(content) / (1024 * 1024)
    if file_size_mb > settings.max_file_size_mb:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {file_size_mb:.2f}MB. Maximum allowed: {settings.max_file_size_mb}MB",
        )

    try:
        decoded_content = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="File encoding error. Please ensure file is UTF-8 encoded.",
        )

    try:
        row_count = len(
            [row for row in csv.reader(decoded_content.splitlines()) if row]
        )
        if row_count > settings.max_dataset_rows:
            raise HTTPException(
                status_code=413,
                detail=f"Too many rows: {row_count}. Maximum allowed: {settings.max_dataset_rows}",
            )
    except csv.Error as e:
        raise HTTPException(status_code=400, detail=f"CSV parsing error: {str(e)}")

    job_id = job_manager.create_job(
        filename=file.filename,
        metadata={"row_count": row_count, "file_size_mb": file_size_mb},
    )

    background_tasks.add_task(
        process_embedding_job,
        job_id,
        decoded_content,
        file.filename,
        pinata_service,
        job_manager,
        llm_service,
    )

    return JobResponse(job_id=job_id, status=JobStatus.QUEUED.value)


@router.post("/embed/query", response_model=QueryEmbeddingResponse)
async def embed_query(
    request: QueryEmbeddingRequest,
    llm_service: LLMService = Depends(get_llm_service),
):
    """Embed a query for retrieval.

    Args:
        request (QueryEmbeddingRequest): Query embedding request
        llm_service (LLMService): LLM service instance

    Returns:
        QueryEmbeddingResponse: Complete response with embedding, and vectorSpec
    """
    query_embedding, dimension = llm_service.generate_single_embedding(request.query)

    settings = get_settings()
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
    job = job_manager.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    response = JobStatusResponse(
        job_id=job.job_id,
        status=job.status.value,
        filename=job.filename,
        created_at=job.created_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        error=job.error,
    )

    if job.status == JobStatus.COMPLETED and job.result:
        response.vector_spec = VectorSpec(**job.result["vectorSpec"])
        response.stats = DatasetStats(**job.result["stats"])
        response.signature = SignatureInfo(**job.result["signature"])

    return response
