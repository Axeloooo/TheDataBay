import asyncio
import io

import pytest
from fastapi import BackgroundTasks, UploadFile, HTTPException

from app.schemas.job_schema import JobStatus
from app.services import llm_job_service


def make_upload_file(name: str, content: bytes) -> UploadFile:
    return UploadFile(filename=name, file=io.BytesIO(content))


def test_enqueue_batch_job_success(settings, job_manager):
    file = make_upload_file("data.csv", b"col1,col2\n1,2\n3,4\n")
    tasks = BackgroundTasks()

    response = asyncio.run(
        llm_job_service.enqueue_batch_job(
            file=file,
            background_tasks=tasks,
            settings=settings,
            job_manager=job_manager,
        )
    )

    assert response.status == JobStatus.QUEUED.value
    assert job_manager.get_job(response.job_id) is not None
    assert len(tasks.tasks) == 1


def test_enqueue_batch_job_invalid_extension(settings, job_manager):
    file = make_upload_file("data.txt", b"hello")
    tasks = BackgroundTasks()

    with pytest.raises(HTTPException):
        asyncio.run(
            llm_job_service.enqueue_batch_job(
                file=file,
                background_tasks=tasks,
                settings=settings,
                job_manager=job_manager,
            )
        )


def test_enqueue_batch_job_too_large(settings, job_manager):
    file = make_upload_file("data.csv", b"x" * 10)
    tasks = BackgroundTasks()

    tiny_settings = settings.model_copy(update={"max_file_size_mb": 0})

    with pytest.raises(HTTPException):
        asyncio.run(
            llm_job_service.enqueue_batch_job(
                file=file,
                background_tasks=tasks,
                settings=tiny_settings,
                job_manager=job_manager,
            )
        )


def test_enqueue_batch_job_decode_error(settings, job_manager):
    file = make_upload_file("data.csv", b"\xff\xfe\xff")
    tasks = BackgroundTasks()

    with pytest.raises(HTTPException):
        asyncio.run(
            llm_job_service.enqueue_batch_job(
                file=file,
                background_tasks=tasks,
                settings=settings,
                job_manager=job_manager,
            )
        )


def test_enqueue_batch_job_too_many_rows(settings, job_manager):
    file = make_upload_file("data.csv", b"a,b\n1,2\n")
    tasks = BackgroundTasks()

    strict_settings = settings.model_copy(update={"max_dataset_rows": 1})

    with pytest.raises(HTTPException):
        asyncio.run(
            llm_job_service.enqueue_batch_job(
                file=file,
                background_tasks=tasks,
                settings=strict_settings,
                job_manager=job_manager,
            )
        )


def test_get_job_status_completed(settings, job_manager):
    job_id = job_manager.create_job(filename="data.csv")
    job_manager.set_result(
        job_id,
        {
            "vectorSpec": {"model": settings.embedding_model, "dimension": 2},
            "stats": {
                "total_rows": 2,
                "total_columns": 2,
                "empty_rows_skipped": 0,
                "has_header": True,
            },
            "signature": {
                "signature_url": "ipfs://QmHash",
                "signature_hash": "0xabc",
            },
        },
    )
    job_manager.update_status(job_id, JobStatus.COMPLETED)

    response = llm_job_service.get_job_status(job_id, job_manager)

    assert response.status == JobStatus.COMPLETED.value
    assert response.vector_spec is not None
    assert response.signature is not None


def test_process_embedding_job_success(monkeypatch, settings, job_manager):
    job_id = job_manager.create_job(filename="data.csv")

    def fake_parse_dataset_file(content, filename):
        return [["1", "2"]], ["col1", "col2"], True, 0

    def fake_record_to_text(record, columns):
        return "col1: 1 | col2: 2"

    async def fake_generate_embeddings_chunked(texts, settings):
        return [[0.1, 0.2]], 2

    async def fake_upload_signature(embeddings, filename, settings, compress=True):
        return "ipfs://QmHash", "0xabc"

    monkeypatch.setattr(llm_job_service, "parse_dataset_file", fake_parse_dataset_file)
    monkeypatch.setattr(llm_job_service, "record_to_text", fake_record_to_text)
    monkeypatch.setattr(
        llm_job_service, "generate_embeddings_chunked", fake_generate_embeddings_chunked
    )
    monkeypatch.setattr(llm_job_service, "upload_signature", fake_upload_signature)

    asyncio.run(
        llm_job_service._process_embedding_job(
            job_id=job_id,
            content="col1,col2\n1,2\n",
            filename="data.csv",
            settings=settings,
            job_manager=job_manager,
        )
    )

    job = job_manager.get_job(job_id)
    assert job.status == JobStatus.COMPLETED
    assert job.result["signature"]["signature_url"] == "ipfs://QmHash"


def test_process_embedding_job_failure(monkeypatch, settings, job_manager):
    job_id = job_manager.create_job(filename="data.csv")

    def fake_parse_dataset_file(content, filename):
        return [["1", "2"]], ["col1", "col2"], True, 0

    async def fake_generate_embeddings_chunked(texts, settings):
        raise RuntimeError("boom")

    monkeypatch.setattr(llm_job_service, "parse_dataset_file", fake_parse_dataset_file)
    monkeypatch.setattr(
        llm_job_service, "generate_embeddings_chunked", fake_generate_embeddings_chunked
    )

    asyncio.run(
        llm_job_service._process_embedding_job(
            job_id=job_id,
            content="col1,col2\n1,2\n",
            filename="data.csv",
            settings=settings,
            job_manager=job_manager,
        )
    )

    job = job_manager.get_job(job_id)
    assert job.status == JobStatus.FAILED
    assert job.error is not None
