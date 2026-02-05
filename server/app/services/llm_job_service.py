"""
LLM job orchestration service for async embedding workflows.
"""

from functools import lru_cache
import csv

from fastapi import BackgroundTasks, Depends, HTTPException, UploadFile

from ..config.settings import Settings, get_settings
from ..schemas.job_schema import JobResponse, JobStatus, JobStatusResponse
from ..schemas.llm_schema import DatasetStats, SignatureInfo, VectorSpec
from ..services.job_manager import JobManager, get_job_manager
from ..services.llm_service import LLMService, get_llm_service
from ..services.pinata_service import PinataService, get_pinata_service


class LLMJobService:
    """Service for managing async LLM embedding jobs."""

    def __init__(
        self,
        settings: Settings,
        job_manager: JobManager,
        llm_service: LLMService,
        pinata_service: PinataService,
    ) -> None:
        """Constructor for LLMJobService.

        Args:
            settings (Settings): Application settings
            job_manager (JobManager): Job management service
            llm_service (LLMService): LLM processing service
            pinata_service (PinataService): Pinata IPFS service
        """
        self.settings = settings
        self.job_manager = job_manager
        self.llm_service = llm_service
        self.pinata_service = pinata_service

    async def enqueue_batch_job(
        self, file: UploadFile, background_tasks: BackgroundTasks
    ) -> JobResponse:
        """Validate input file and enqueue async embedding job.

        Args:
            file (UploadFile): Dataset file upload
            background_tasks (BackgroundTasks): FastAPI background tasks

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
        except Exception as exc:
            raise HTTPException(
                status_code=400, detail=f"Error reading file: {str(exc)}"
            ) from exc

        file_size_mb = len(content) / (1024 * 1024)
        if file_size_mb > self.settings.max_file_size_mb:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"File too large: {file_size_mb:.2f}MB. "
                    f"Maximum allowed: {self.settings.max_file_size_mb}MB"
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
            if row_count > self.settings.max_dataset_rows:
                raise HTTPException(
                    status_code=413,
                    detail=(
                        f"Too many rows: {row_count}. "
                        f"Maximum allowed: {self.settings.max_dataset_rows}"
                    ),
                )
        except csv.Error as exc:
            raise HTTPException(
                status_code=400, detail=f"CSV parsing error: {str(exc)}"
            ) from exc

        job_id = self.job_manager.create_job(
            filename=file.filename,
            metadata={"row_count": row_count, "file_size_mb": file_size_mb},
        )

        background_tasks.add_task(
            self._process_embedding_job,
            job_id,
            decoded_content,
            file.filename,
        )

        return JobResponse(job_id=job_id, status=JobStatus.QUEUED.value)

    def get_job_status(self, job_id: str) -> JobStatusResponse:
        """Poll job status and retrieve results.

        Args:
            job_id (str): Job identifier

        Returns:
            JobStatusResponse: Job status and result details
        """
        job = self.job_manager.get_job(job_id)

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

    async def _process_embedding_job(
        self,
        job_id: str,
        content: str,
        filename: str,
    ) -> None:
        """Background task to process embedding job.

        Args:
            job_id (str): Job identifier
            content (str): File content
            filename (str): Original filename
        """
        try:
            # Update job status to running
            self.job_manager.update_status(job_id, JobStatus.RUNNING)

            # Parse dataset
            data_rows, column_names, has_header, empty_rows_skipped = (
                self.llm_service.parse_dataset_file(content, filename)
            )

            # Transform to text
            texts = []
            for row in data_rows:
                text = self.llm_service.record_to_text(row, column_names)
                texts.append(text)

            # Generate embeddings with chunking
            embeddings, dimension = await self.llm_service.generate_embeddings_chunked(
                texts
            )

            # Upload to IPFS
            ipfs_url, signature_hash = await self.pinata_service.upload_signature(
                embeddings, filename, compress=True
            )

            # Build result
            result = {
                "vectorSpec": {
                    "model": self.settings.embedding_model,
                    "dimension": dimension,
                },
                "stats": {
                    "total_rows": len(data_rows),
                    "total_columns": len(column_names),
                    "empty_rows_skipped": empty_rows_skipped,
                    "has_header": has_header,
                },
                "signature": {
                    "signature_url": ipfs_url,
                    "signature_hash": signature_hash,
                },
            }

            # Mark job as completed
            self.job_manager.set_result(job_id, result)
            self.job_manager.update_status(job_id, JobStatus.COMPLETED)

        except Exception as exc:
            # Mark job as failed
            self.job_manager.set_error(job_id, str(exc))


@lru_cache(maxsize=1)
def get_llm_job_service(
    settings: Settings = Depends(get_settings),
    job_manager: JobManager = Depends(get_job_manager),
    llm_service: LLMService = Depends(get_llm_service),
    pinata_service: PinataService = Depends(get_pinata_service),
) -> LLMJobService:
    """Get singleton LLMJobService instance.

    Args:
        settings (Settings, optional): Application settings. Defaults to Depends(get_settings).
        job_manager (JobManager, optional): Job management service. Defaults to Depends(get_job_manager).
        llm_service (LLMService, optional): LLM processing service. Defaults to Depends(get_llm_service).
        pinata_service (PinataService, optional): Pinata IPFS service. Defaults to Depends(get_pinata_service).

    Returns:
        LLMJobService: LLM job service instance
    """
    return LLMJobService(settings, job_manager, llm_service, pinata_service)
