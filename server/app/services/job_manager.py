"""
Job manager for tracking async embedding jobs.
"""

import uuid
from datetime import datetime
from typing import Dict, Optional, Any
from functools import lru_cache
from ..schemas.job_schema import Job, JobStatus


class JobManager:
    """
    In-memory job manager for tracking embedding jobs.
    Designed to be easily swapped with Redis/Celery backend.
    """

    def __init__(self):
        """Constructor for JobManager."""
        self._jobs: Dict[str, Job] = {}

    def create_job(
        self, filename: str, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new job and return its ID.

        Args:
            filename (str): Name of the file being processed
            metadata (Optional[Dict[str, Any]]): Optional metadata to store with the job

        Returns:
            str: Unique job identifier
        """
        job_id = str(uuid.uuid4())
        job = Job(
            job_id=job_id,
            status=JobStatus.QUEUED,
            filename=filename,
            created_at=datetime.utcnow(),
            metadata=metadata or {},
        )
        self._jobs[job_id] = job
        return job_id

    def get_job(self, job_id: str) -> Optional[Job]:
        """Retrieve a job by ID.

        Args:
            job_id (str): Job identifier

        Returns:
            Optional[Job]: Job object or None if not found
        """
        return self._jobs.get(job_id)

    def update_status(self, job_id: str, status: JobStatus) -> None:
        """Update job status.

        Args:
            job_id (str): Job identifier
            status (JobStatus): New status
        """
        job = self._jobs.get(job_id)
        if not job:
            return

        job.status = status

        if status == JobStatus.RUNNING:
            job.started_at = datetime.utcnow()
        elif status in (JobStatus.COMPLETED, JobStatus.FAILED):
            job.completed_at = datetime.utcnow()

    def set_result(self, job_id: str, result: Dict[str, Any]) -> None:
        """Set job result data.

        Args:
            job_id (str): Job identifier
            result (Dict[str, Any]): Result data to store
        """
        job = self._jobs.get(job_id)
        if job:
            job.result = result

    def set_error(self, job_id: str, error: str) -> None:
        """Set job error message and mark as failed.

        Args:
            job_id (str): Job identifier
            error (str): Error message
        """
        job = self._jobs.get(job_id)
        if job:
            job.error = error
            job.status = JobStatus.FAILED
            job.completed_at = datetime.utcnow()

    def delete_job(self, job_id: str) -> None:
        """Delete a job from the store.

        Args:
            job_id (str): Job identifier
        """
        self._jobs.pop(job_id, None)

    def get_all_jobs(self) -> Dict[str, Job]:
        """Get all jobs (for debugging/admin purposes).

        Returns:
            Dict[str, Job]: Dictionary of all jobs
        """
        return self._jobs.copy()


@lru_cache(maxsize=1)
def get_job_manager() -> JobManager:
    """Get singleton JobManager instance.

    Returns:
        JobManager: Singleton JobManager instance
    """
    return JobManager()
