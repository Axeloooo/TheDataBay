"""
LLM job orchestration functions for async embedding workflows.
"""

import base64
import csv
import logging
import uuid

from fastapi import BackgroundTasks, HTTPException, UploadFile
from langchain_core.documents import Document
from sqlalchemy import text
from web3 import Web3

from ..config.settings import Settings
from ..database.async_engine import get_async_session_factory
from ..schemas.job_schema import JobResponse, JobStatus, JobStatusResponse
from ..schemas.llm_schema import DatasetStats, VectorSpec
from .dataset_key_repo import async_upsert_dataset_key
from ..services.encryption_service import encrypt_bytes, generate_key
from ..services.job_manager import JobManager
from ..services.llm_service import (
    EMBEDDING_DIMENSION,
    DATASET_ROWS_COLLECTION,
    parse_dataset_file,
    record_to_text,
    vectorstore_for_settings,
)
from ..services.pinata_service import upload_bytes

logger = logging.getLogger(__name__)


async def enqueue_batch_job(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    settings: Settings,
    job_manager: JobManager,
    title: str,
    description: str,
    seller: str,
    price: int,
    seller_wallet_type: str = "evm",
) -> JobResponse:
    """Validate input file and enqueue async embedding job.

    Args:
        file (UploadFile): Dataset file upload
        background_tasks (BackgroundTasks): FastAPI background tasks
        settings (Settings): Application settings instance
        job_manager (JobManager): Job manager instance
        title (str): Dataset title
        description (str): Dataset description
        seller (str): Seller EVM address
        price (int): Price in settlement token atomic units
        seller_wallet_type (str): Seller wallet type (evm only for now)

    Returns:
        JobResponse: Job submission response with job ID
    """

    normalized_wallet_type = seller_wallet_type.strip().lower()
    logger.info(
        "llm_job.enqueue called filename=%s seller=%s wallet_type=%s",
        file.filename,
        seller,
        normalized_wallet_type,
    )
    if normalized_wallet_type != "evm":
        raise HTTPException(
            status_code=400,
            detail="Only EVM seller addresses are supported for now.",
        )
    if not Web3.is_address(seller):
        raise HTTPException(status_code=400, detail="Invalid EVM seller address.")

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
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail=f"Error reading file: {str(exc)}"
        ) from exc

    file_size_mb = len(content) / (1024 * 1024)
    if file_size_mb > settings.max_file_size_mb:
        raise HTTPException(
            status_code=413,
            detail=(
                f"File too large: {file_size_mb:.2f}MB. "
                f"Maximum allowed: {settings.max_file_size_mb}MB"
            ),
        )

    try:
        decoded_content = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail="File encoding error. Please ensure file is UTF-8 encoded.",
        ) from exc

    try:
        row_count = len(
            [row for row in csv.reader(decoded_content.splitlines()) if row]
        )
        if row_count > settings.max_dataset_rows:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"Too many rows: {row_count}. "
                    f"Maximum allowed: {settings.max_dataset_rows}"
                ),
            )
    except csv.Error as exc:
        raise HTTPException(
            status_code=400, detail=f"CSV parsing error: {str(exc)}"
        ) from exc

    listing_id = str(uuid.uuid4())

    job_id = job_manager.create_job(
        filename=file.filename,
        metadata={
            "row_count": row_count,
            "file_size_mb": file_size_mb,
            "listing_id": listing_id,
        },
    )

    background_tasks.add_task(
        _process_embedding_job,
        job_id,
        content,
        file.filename,
        settings,
        job_manager,
        listing_id,
        title,
        description,
        seller,
        price,
    )

    return JobResponse(
        job_id=job_id,
        status=JobStatus.QUEUED.value,
        listing_id=listing_id,
    )


def get_job_status(job_id: str, job_manager: JobManager) -> JobStatusResponse:
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
        listing_id=(job.metadata or {}).get("listing_id"),
    )

    if not response.listing_id and job.result:
        response.listing_id = job.result.get("listing_id")

    if job.status == JobStatus.COMPLETED and job.result:
        dataset = job.result.get("dataset") or {}
        response.dataset_url = dataset.get("dataset_url")
        response.dataset_hash = dataset.get("dataset_hash")
        response.vector_spec = VectorSpec(**job.result["vectorSpec"])
        response.stats = DatasetStats(**job.result["stats"])

    return response


async def delete_listing_documents(listing_id: str) -> None:
    """Delete prior LangChain PGVector row documents for one listing."""
    factory = get_async_session_factory()
    async with factory() as session:
        async with session.begin():
            await session.execute(
                text(
                    """
                    DELETE FROM langchain_pg_embedding e
                    USING langchain_pg_collection c
                    WHERE e.collection_id = c.uuid
                      AND c.name = :collection_name
                      AND e.cmetadata->>'listing_id' = :listing_id
                    """
                ),
                {
                    "collection_name": DATASET_ROWS_COLLECTION,
                    "listing_id": listing_id,
                },
            )


async def _process_embedding_job(
    job_id: str,
    content_bytes: bytes,
    filename: str,
    settings: Settings,
    job_manager: JobManager,
    listing_id: str,
    title: str,
    description: str,
    seller: str,
    price: int,
) -> None:
    """Background task to process embedding job.

    The job owns its own async database session for DatasetKey persistence.
    PGVector manages its own connection, so DatasetKey is written last after
    vector ingest succeeds. A retry deletes stale row vectors before ingest.

    Args:
        job_id (str): Job identifier
        content_bytes (bytes): Raw file bytes
        filename (str): Original filename
        settings (Settings): Application settings instance
        job_manager (JobManager): Job manager instance
        listing_id (str): Listing UUID string
        title (str): Dataset title
        description (str): Dataset description
        seller (str): Seller EVM address
        price (int): Price in settlement token atomic units
    """
    logger.info("llm_job.process start job_id=%s listing_id=%s", job_id, listing_id)

    try:
        # Update job status to running
        job_manager.update_status(job_id, JobStatus.RUNNING)

        # Decode content for parsing/embedding
        decoded_content = content_bytes.decode("utf-8")

        # Parse dataset
        data_rows, column_names, has_header, empty_rows_skipped = parse_dataset_file(
            decoded_content
        )

        documents = [
            Document(
                page_content=record_to_text(row, column_names),
                metadata={"listing_id": listing_id, "row_index": i},
            )
            for i, row in enumerate(data_rows)
        ]
        document_ids = [f"{listing_id}:{i}" for i in range(len(documents))]

        # Encrypt raw dataset bytes and upload to IPFS
        aad = listing_id.encode("utf-8")
        key = generate_key()
        ciphertext, nonce = encrypt_bytes(content_bytes, key, aad)
        dataset_url, dataset_hash = await upload_bytes(ciphertext, filename, settings)

        await delete_listing_documents(listing_id)
        await vectorstore_for_settings(settings).aadd_documents(
            documents,
            ids=document_ids,
        )

        # Prepare key material
        key_b64 = base64.b64encode(key).decode("utf-8")
        nonce_b64 = base64.b64encode(nonce).decode("utf-8")

        # Persist DatasetKey after vector ingest succeeds.
        factory = get_async_session_factory()
        async with factory() as session:
            async with session.begin():
                await async_upsert_dataset_key(
                    db=session,
                    listing_id=listing_id,
                    key_b64=key_b64,
                    nonce_b64=nonce_b64,
                    dataset_url=dataset_url,
                    dataset_hash=dataset_hash,
                )

        # Build result
        result = {
            "listing_id": listing_id,
            "dataset": {
                "dataset_url": dataset_url,
                "dataset_hash": dataset_hash,
            },
            "vectorSpec": {
                "model": settings.embedding_model,
                "dimension": EMBEDDING_DIMENSION,
            },
            "stats": {
                "total_rows": len(data_rows),
                "total_columns": len(column_names),
                "empty_rows_skipped": empty_rows_skipped,
                "has_header": has_header,
            },
        }

        # Mark job as completed
        job_manager.set_result(job_id, result)
        job_manager.update_status(job_id, JobStatus.COMPLETED)
        logger.info(
            "llm_job.process completed job_id=%s listing_id=%s rows=%s",
            job_id,
            listing_id,
            len(data_rows),
        )

    except Exception as exc:
        # Mark job as failed
        job_manager.set_error(job_id, str(exc))
        logger.exception(
            "llm_job.process failed job_id=%s listing_id=%s",
            job_id,
            listing_id,
        )
