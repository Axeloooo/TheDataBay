import io
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import BackgroundTasks, UploadFile, HTTPException

from app.schemas.job_schema import JobStatus
from app.services import llm_job_service


def make_upload_file(name: str, content: bytes) -> UploadFile:
    return UploadFile(filename=name, file=io.BytesIO(content))


@pytest.mark.asyncio
async def test_enqueue_batch_job_success(settings, job_manager):
    file = make_upload_file("data.csv", b"col1,col2\n1,2\n3,4\n")
    tasks = BackgroundTasks()

    response = await llm_job_service.enqueue_batch_job(
        file=file,
        background_tasks=tasks,
        settings=settings,
        job_manager=job_manager,
        title="Dataset",
        description="Desc",
        seller="0x0000000000000000000000000000000000000001",
        price=100,
    )

    assert response.status == JobStatus.QUEUED.value
    assert job_manager.get_job(response.job_id) is not None
    assert len(tasks.tasks) == 1
    assert response.listing_id is not None


@pytest.mark.asyncio
async def test_enqueue_batch_job_invalid_extension(settings, job_manager):
    file = make_upload_file("data.txt", b"hello")
    tasks = BackgroundTasks()

    with pytest.raises(HTTPException):
        await llm_job_service.enqueue_batch_job(
            file=file,
            background_tasks=tasks,
            settings=settings,
            job_manager=job_manager,
            title="Dataset",
            description="Desc",
            seller="0x0000000000000000000000000000000000000001",
            price=100,
        )


@pytest.mark.asyncio
async def test_enqueue_batch_job_rejects_non_evm_wallet(settings, job_manager):
    file = make_upload_file("data.csv", b"col1,col2\n1,2\n")
    tasks = BackgroundTasks()

    with pytest.raises(HTTPException):
        await llm_job_service.enqueue_batch_job(
            file=file,
            background_tasks=tasks,
            settings=settings,
            job_manager=job_manager,
            title="Dataset",
            description="Desc",
            seller="0x0000000000000000000000000000000000000001",
            price=100,
            seller_wallet_type="solana",
        )


@pytest.mark.asyncio
async def test_enqueue_batch_job_too_large(settings, job_manager):
    file = make_upload_file("data.csv", b"x" * 10)
    tasks = BackgroundTasks()

    tiny_settings = settings.model_copy(update={"max_file_size_mb": 0})

    with pytest.raises(HTTPException):
        await llm_job_service.enqueue_batch_job(
            file=file,
            background_tasks=tasks,
            settings=tiny_settings,
            job_manager=job_manager,
            title="Dataset",
            description="Desc",
            seller="0x0000000000000000000000000000000000000001",
            price=100,
        )


@pytest.mark.asyncio
async def test_enqueue_batch_job_decode_error(settings, job_manager):
    file = make_upload_file("data.csv", b"\xff\xfe\xff")
    tasks = BackgroundTasks()

    with pytest.raises(HTTPException):
        await llm_job_service.enqueue_batch_job(
            file=file,
            background_tasks=tasks,
            settings=settings,
            job_manager=job_manager,
            title="Dataset",
            description="Desc",
            seller="0x0000000000000000000000000000000000000001",
            price=100,
        )


@pytest.mark.asyncio
async def test_enqueue_batch_job_too_many_rows(settings, job_manager):
    file = make_upload_file("data.csv", b"a,b\n1,2\n")
    tasks = BackgroundTasks()

    strict_settings = settings.model_copy(update={"max_dataset_rows": 1})

    with pytest.raises(HTTPException):
        await llm_job_service.enqueue_batch_job(
            file=file,
            background_tasks=tasks,
            settings=strict_settings,
            job_manager=job_manager,
            title="Dataset",
            description="Desc",
            seller="0x0000000000000000000000000000000000000001",
            price=100,
        )


def test_get_job_status_completed(settings, job_manager):
    job_id = job_manager.create_job(
        filename="data.csv",
        metadata={"listing_id": "123e4567-e89b-12d3-a456-426614174000"},
    )
    job_manager.set_result(
        job_id,
        {
            "listing_id": "123e4567-e89b-12d3-a456-426614174000",
            "dataset": {"dataset_url": "ipfs://QmData", "dataset_hash": "0xdata"},
            "vectorSpec": {"model": settings.embedding_model, "dimension": 2},
            "stats": {
                "total_rows": 2,
                "total_columns": 2,
                "empty_rows_skipped": 0,
                "has_header": True,
            },
        },
    )
    job_manager.update_status(job_id, JobStatus.COMPLETED)

    response = llm_job_service.get_job_status(job_id, job_manager)

    assert response.status == JobStatus.COMPLETED.value
    assert response.dataset_url == "ipfs://QmData"
    assert response.vector_spec is not None
    assert response.listing_id == "123e4567-e89b-12d3-a456-426614174000"


def _make_fake_session_factory():
    """Return a factory whose sessions are fully mocked async context managers."""
    fake_session = AsyncMock()
    fake_session.__aenter__ = AsyncMock(return_value=fake_session)
    fake_session.__aexit__ = AsyncMock(return_value=False)

    fake_begin_ctx = AsyncMock()
    fake_begin_ctx.__aenter__ = AsyncMock(return_value=None)
    fake_begin_ctx.__aexit__ = AsyncMock(return_value=False)
    fake_session.begin = MagicMock(return_value=fake_begin_ctx)

    def factory():
        return fake_session

    return factory, fake_session


@pytest.mark.asyncio
async def test_process_embedding_job_success(monkeypatch, settings, job_manager):
    job_id = job_manager.create_job(filename="data.csv")

    def fake_parse_dataset_file(content):
        return [["1", "2"]], ["col1", "col2"], True, 0

    def fake_record_to_text(record, columns):
        return "col1: 1 | col2: 2"

    def fake_generate_key():
        return b"k" * 32

    def fake_encrypt_bytes(content_bytes, key, aad):
        return b"ciphertext", b"nonce12345678"

    async def fake_upload_bytes(payload, filename, settings):
        return "ipfs://QmData", "0xdata"

    async def fake_async_upsert_dataset_key(**kwargs):
        return None

    delete_calls: list[str] = []

    async def fake_delete_listing_documents(listing_id):
        delete_calls.append(listing_id)

    fake_vectorstore = AsyncMock()
    fake_vectorstore.aadd_documents = AsyncMock(return_value=None)

    fake_factory, _fake_session = _make_fake_session_factory()

    monkeypatch.setattr(llm_job_service, "parse_dataset_file", fake_parse_dataset_file)
    monkeypatch.setattr(llm_job_service, "record_to_text", fake_record_to_text)
    monkeypatch.setattr(llm_job_service, "generate_key", fake_generate_key)
    monkeypatch.setattr(llm_job_service, "encrypt_bytes", fake_encrypt_bytes)
    monkeypatch.setattr(llm_job_service, "upload_bytes", fake_upload_bytes)
    monkeypatch.setattr(
        llm_job_service, "async_upsert_dataset_key", fake_async_upsert_dataset_key
    )
    monkeypatch.setattr(
        llm_job_service, "delete_listing_documents", fake_delete_listing_documents
    )
    monkeypatch.setattr(
        llm_job_service, "vectorstore_for_settings", lambda settings: fake_vectorstore
    )
    monkeypatch.setattr(
        llm_job_service, "get_async_session_factory", lambda: fake_factory
    )

    listing_id = "123e4567-e89b-12d3-a456-426614174000"
    await llm_job_service._process_embedding_job(
        job_id=job_id,
        content_bytes=b"col1,col2\n1,2\n",
        filename="data.csv",
        settings=settings,
        job_manager=job_manager,
        listing_id=listing_id,
        title="Dataset",
        description="Desc",
        seller="0x0000000000000000000000000000000000000001",
        price=100,
    )

    job = job_manager.get_job(job_id)
    assert job.status == JobStatus.COMPLETED
    assert "signature" not in job.result
    assert delete_calls == [listing_id]
    fake_vectorstore.aadd_documents.assert_awaited_once()
    docs = fake_vectorstore.aadd_documents.await_args.args[0]
    ids = fake_vectorstore.aadd_documents.await_args.kwargs["ids"]
    assert [doc.page_content for doc in docs] == ["col1: 1 | col2: 2"]
    assert docs[0].metadata == {"listing_id": listing_id, "row_index": 0}
    assert ids == [f"{listing_id}:0"]


@pytest.mark.asyncio
async def test_process_embedding_job_failure(monkeypatch, settings, job_manager):
    job_id = job_manager.create_job(filename="data.csv")

    def fake_parse_dataset_file(content):
        return [["1", "2"]], ["col1", "col2"], True, 0

    async def fake_upload_bytes(payload, filename, settings):
        raise RuntimeError("boom")

    monkeypatch.setattr(llm_job_service, "parse_dataset_file", fake_parse_dataset_file)
    monkeypatch.setattr(llm_job_service, "upload_bytes", fake_upload_bytes)

    await llm_job_service._process_embedding_job(
        job_id=job_id,
        content_bytes=b"col1,col2\n1,2\n",
        filename="data.csv",
        settings=settings,
        job_manager=job_manager,
        listing_id="123e4567-e89b-12d3-a456-426614174000",
        title="Dataset",
        description="Desc",
        seller="0x0000000000000000000000000000000000000001",
        price=100,
    )

    job = job_manager.get_job(job_id)
    assert job.status == JobStatus.FAILED
    assert job.error is not None


@pytest.mark.asyncio
async def test_process_embedding_job_key_not_written_when_vector_ingest_fails(
    monkeypatch, settings, job_manager
):
    """DatasetKey is written last, so vector ingest failure leaves no key row."""
    job_id = job_manager.create_job(filename="data.csv")

    def fake_parse_dataset_file(content):
        return [["1", "2"]], ["col1", "col2"], True, 0

    def fake_record_to_text(record, columns):
        return "col1: 1 | col2: 2"

    def fake_generate_key():
        return b"k" * 32

    def fake_encrypt_bytes(content_bytes, key, aad):
        return b"ciphertext", b"nonce12345678"

    async def fake_upload_bytes(payload, filename, settings):
        return "ipfs://QmData", "0xdata"

    key_upsert_calls: list = []

    async def fake_async_upsert_dataset_key(**kwargs):
        key_upsert_calls.append(kwargs)
        return None

    async def fake_delete_listing_documents(listing_id):
        return None

    fake_vectorstore = AsyncMock()
    fake_vectorstore.aadd_documents = AsyncMock(side_effect=RuntimeError("DB write failed"))

    monkeypatch.setattr(llm_job_service, "parse_dataset_file", fake_parse_dataset_file)
    monkeypatch.setattr(llm_job_service, "record_to_text", fake_record_to_text)
    monkeypatch.setattr(llm_job_service, "generate_key", fake_generate_key)
    monkeypatch.setattr(llm_job_service, "encrypt_bytes", fake_encrypt_bytes)
    monkeypatch.setattr(llm_job_service, "upload_bytes", fake_upload_bytes)
    monkeypatch.setattr(
        llm_job_service, "async_upsert_dataset_key", fake_async_upsert_dataset_key
    )
    monkeypatch.setattr(
        llm_job_service, "delete_listing_documents", fake_delete_listing_documents
    )
    monkeypatch.setattr(llm_job_service, "vectorstore_for_settings", lambda settings: fake_vectorstore)

    await llm_job_service._process_embedding_job(
        job_id=job_id,
        content_bytes=b"col1,col2\n1,2\n",
        filename="data.csv",
        settings=settings,
        job_manager=job_manager,
        listing_id="123e4567-e89b-12d3-a456-426614174000",
        title="Dataset",
        description="Desc",
        seller="0x0000000000000000000000000000000000000001",
        price=100,
    )

    job = job_manager.get_job(job_id)
    assert job.status == JobStatus.FAILED
    assert key_upsert_calls == []
