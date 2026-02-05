from app.services.job_manager import JobManager
from app.schemas.job_schema import JobStatus


def test_create_and_get_job():
    manager = JobManager()
    job_id = manager.create_job(filename="file.csv", metadata={"row_count": 2})

    job = manager.get_job(job_id)
    assert job is not None
    assert job.filename == "file.csv"
    assert job.status == JobStatus.QUEUED
    assert job.metadata["row_count"] == 2


def test_update_status_sets_timestamps():
    manager = JobManager()
    job_id = manager.create_job(filename="file.csv")

    manager.update_status(job_id, JobStatus.RUNNING)
    job = manager.get_job(job_id)
    assert job.started_at is not None

    manager.update_status(job_id, JobStatus.COMPLETED)
    job = manager.get_job(job_id)
    assert job.completed_at is not None


def test_set_error_marks_failed():
    manager = JobManager()
    job_id = manager.create_job(filename="file.csv")

    manager.set_error(job_id, "boom")
    job = manager.get_job(job_id)

    assert job.status == JobStatus.FAILED
    assert job.error == "boom"
    assert job.completed_at is not None


def test_delete_job():
    manager = JobManager()
    job_id = manager.create_job(filename="file.csv")
    manager.delete_job(job_id)

    assert manager.get_job(job_id) is None


def test_get_all_jobs_returns_copy():
    manager = JobManager()
    manager.create_job(filename="file.csv")
    jobs = manager.get_all_jobs()

    assert isinstance(jobs, dict)
    jobs.clear()
    assert len(manager.get_all_jobs()) == 1
