from types import SimpleNamespace
import io

import pytest
from fastapi import UploadFile
from langchain_core.documents import Document

from app.datasets.service import DatasetEmbedService
from app.shared.errors import ApiError


def make_upload_file(name: str, content: bytes) -> UploadFile:
    return UploadFile(filename=name, file=io.BytesIO(content))


class FakeVectorstore:
    def __init__(self) -> None:
        self.create_called = False
        self.added_docs = []
        self.added_ids = []

    async def acreate_collection(self) -> None:
        self.create_called = True

    async def aadd_documents(self, documents, ids) -> None:
        self.added_docs = documents
        self.added_ids = ids


class FakeCSVLoader:
    loaded_paths: list[str] = []

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path

    def load(self) -> list[Document]:
        self.loaded_paths.append(self.file_path)
        return [
            Document(
                page_content="age: 63\ncp: 3",
                metadata={"source": self.file_path, "row": 0},
            ),
            Document(
                page_content="age: 37\ncp: 2",
                metadata={"source": self.file_path, "row": 1},
            ),
        ]


class FakeTextSplitter:
    def __init__(self) -> None:
        self.input_docs: list[Document] = []

    def split_documents(self, documents: list[Document]) -> list[Document]:
        self.input_docs = documents
        return [
            Document(
                page_content="split chunk: age = 63; cp = 3 | age = 37; cp = 2",
                metadata={"chunk": 0},
            )
        ]


class FakeKeyRepository:
    def __init__(self) -> None:
        self.calls = []

    async def upsert(self, **kwargs):
        self.calls.append(kwargs)
        return None


class FakeSession:
    def begin(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


def fake_session_factory():
    return FakeSession()


def make_service(settings, **overrides):
    vectorstore = overrides.pop("vectorstore", FakeVectorstore())
    repo = overrides.pop("repo", FakeKeyRepository())
    stale_calls = []
    text_splitter = overrides.pop("text_splitter", FakeTextSplitter())

    async def stale_deleter(listing_id, current_ids, session_factory):
        stale_calls.append((listing_id, current_ids, session_factory))

    async def uploader(payload, filename, settings):
        return "ipfs://QmData", "0xdata"

    service = DatasetEmbedService(
        settings,
        vectorstore_factory=lambda settings: vectorstore,
        session_factory=fake_session_factory,
        key_repository=repo,
        csv_loader_cls=overrides.pop("csv_loader_cls", FakeCSVLoader),
        text_splitter_factory=overrides.pop(
            "text_splitter_factory", lambda settings: text_splitter
        ),
        key_generator=lambda: b"k" * 32,
        encryptor=lambda content, key, aad: (b"ciphertext", b"n" * 12),
        uploader=overrides.pop("uploader", uploader),
        stale_document_deleter=overrides.pop("stale_deleter", stale_deleter),
    )
    return SimpleNamespace(
        service=service,
        vectorstore=vectorstore,
        repo=repo,
        stale_calls=stale_calls,
        text_splitter=text_splitter,
    )


@pytest.mark.asyncio
async def test_embed_returns_completed_dataset_response(settings):
    harness = make_service(settings)

    response = await harness.service.embed(
        file=make_upload_file("heart.csv", b"age,cp\n63,3\n37,2\n"),
        title="Heart",
        description="Cardio rows",
        seller="0x0000000000000000000000000000000000000001",
        price_atomic=100,
        settlement_currency="USDC",
        settlement_decimals=6,
    )

    assert response.dataset_url == "ipfs://QmData"
    assert response.dataset_hash == "0xdata"
    assert response.preview.column_names == ["age", "cp"]
    assert response.preview.rows == [["63", "3"], ["37", "2"]]
    assert response.stats.total_rows == 2
    assert response.stats.total_columns == 2
    assert response.vector_spec.model == settings.embedding_model
    assert harness.vectorstore.create_called is True
    assert harness.vectorstore.added_ids == [
        f"{response.listing_id}:row:0",
        f"{response.listing_id}:row:1",
        f"{response.listing_id}:chunk:0",
    ]
    assert harness.vectorstore.added_docs[0].page_content.startswith(
        "title = Heart; description = Cardio rows; age = 63; cp = 3"
    )
    assert "title = Heart; description = Cardio rows; age = 63; cp = 3" in (
        harness.text_splitter.input_docs[0].page_content
    )
    assert harness.vectorstore.added_docs[0].metadata == {
        "listing_id": response.listing_id,
        "doc_type": "row",
        "row_index": 0,
        "row_indexes": [0],
        "columns": ["age", "cp"],
        "numeric_fields": {"age": 63, "cp": 3},
        "text_fields": {},
    }
    assert harness.vectorstore.added_docs[2].metadata == {
        "listing_id": response.listing_id,
        "doc_type": "chunk",
        "chunk_index": 0,
        "row_indexes": [0, 1],
        "columns": ["age", "cp"],
        "numeric_fields": {"age": [63, 37], "cp": [3, 2]},
        "text_fields": {},
    }
    assert harness.vectorstore.added_docs[2].page_content.startswith("split chunk")
    assert harness.stale_calls[0][1] == harness.vectorstore.added_ids
    assert harness.repo.calls[0]["listing_id"] == response.listing_id
    assert harness.repo.calls[0]["dataset_url"] == "ipfs://QmData"
    assert harness.repo.calls[0]["preview"] == {
        "column_names": ["age", "cp"],
        "rows": [["63", "3"], ["37", "2"]],
    }
    assert harness.repo.calls[0]["stats"] == {
        "total_rows": 2,
        "total_columns": 2,
        "has_header": True,
        "empty_rows_skipped": 0,
    }
    assert harness.repo.calls[0]["vector_spec"] == {
        "model": settings.embedding_model,
        "dimension": settings.embedding_dimension,
    }


@pytest.mark.parametrize(
    "filename,content,error,status",
    [
        ("data.txt", b"a,b\n1,2\n", "invalid_file_format", 400),
        ("data.csv", b"\xff\xfe", "encoding_error", 400),
    ],
)
@pytest.mark.asyncio
async def test_embed_validation_errors(settings, filename, content, error, status):
    harness = make_service(settings)

    with pytest.raises(ApiError) as exc_info:
        await harness.service.embed(
            file=make_upload_file(filename, content),
            title="Dataset",
            description="Desc",
            seller="0x0000000000000000000000000000000000000001",
            price_atomic=100,
        )

    assert exc_info.value.error == error
    assert exc_info.value.status_code == status
    assert harness.repo.calls == []


@pytest.mark.asyncio
async def test_embed_rejects_too_large_file(settings):
    strict_settings = settings.model_copy(update={"max_file_size_mb": 0})
    harness = make_service(strict_settings)

    with pytest.raises(ApiError) as exc_info:
        await harness.service.embed(
            file=make_upload_file("data.csv", b"a,b\n1,2\n"),
            title="Dataset",
            description="Desc",
            seller="0x0000000000000000000000000000000000000001",
            price_atomic=100,
        )

    assert exc_info.value.error == "file_too_large"
    assert exc_info.value.status_code == 413
    assert harness.repo.calls == []


@pytest.mark.asyncio
async def test_embed_rejects_too_many_rows(settings):
    strict_settings = settings.model_copy(update={"max_dataset_rows": 1})
    harness = make_service(strict_settings)

    with pytest.raises(ApiError) as exc_info:
        await harness.service.embed(
            file=make_upload_file("data.csv", b"a,b\n1,2\n"),
            title="Dataset",
            description="Desc",
            seller="0x0000000000000000000000000000000000000001",
            price_atomic=100,
        )

    assert exc_info.value.error == "too_many_rows"
    assert exc_info.value.status_code == 413
    assert harness.repo.calls == []


@pytest.mark.parametrize(
    "kwargs,error",
    [
        ({"seller_wallet_type": "solana"}, "unsupported_wallet_type"),
        ({"seller": "not-an-address"}, "invalid_seller_address"),
        ({"settlement_currency": "XYZ"}, "unsupported_currency"),
        (
            {"settlement_currency": "CADC", "settlement_decimals": 6},
            "decimals_mismatch",
        ),
    ],
)
@pytest.mark.asyncio
async def test_embed_rejects_invalid_metadata(settings, kwargs, error):
    harness = make_service(settings)
    payload = {
        "file": make_upload_file("data.csv", b"a,b\n1,2\n"),
        "title": "Dataset",
        "description": "Desc",
        "seller": "0x0000000000000000000000000000000000000001",
        "price_atomic": 100,
    }
    payload.update(kwargs)

    with pytest.raises(ApiError) as exc_info:
        await harness.service.embed(**payload)

    assert exc_info.value.error == error
    assert exc_info.value.status_code == 400
    assert harness.repo.calls == []


@pytest.mark.asyncio
async def test_embed_does_not_write_key_when_vectorstore_fails(settings):
    vectorstore = FakeVectorstore()

    async def fail_add(documents, ids):
        raise RuntimeError("vectorstore down")

    vectorstore.aadd_documents = fail_add
    harness = make_service(settings, vectorstore=vectorstore)

    with pytest.raises(ApiError) as exc_info:
        await harness.service.embed(
            file=make_upload_file("data.csv", b"a,b\n1,2\n"),
            title="Dataset",
            description="Desc",
            seller="0x0000000000000000000000000000000000000001",
            price_atomic=100,
        )

    assert exc_info.value.error == "vectorstore_error"
    assert harness.repo.calls == []


@pytest.mark.asyncio
async def test_embed_maps_ipfs_failure_and_does_not_write_key(settings):
    async def failing_uploader(payload, filename, settings):
        raise RuntimeError("IPFS gateway failed")

    harness = make_service(settings, uploader=failing_uploader)

    with pytest.raises(ApiError) as exc_info:
        await harness.service.embed(
            file=make_upload_file("data.csv", b"a,b\n1,2\n"),
            title="Dataset",
            description="Desc",
            seller="0x0000000000000000000000000000000000000001",
            price_atomic=100,
        )

    assert exc_info.value.error == "ipfs_error"
    assert exc_info.value.status_code == 502
    assert harness.repo.calls == []
