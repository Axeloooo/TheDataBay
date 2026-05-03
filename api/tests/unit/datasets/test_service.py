import io
from types import SimpleNamespace

import pytest
from fastapi import UploadFile
from langchain_core.documents import Document

from app.datasets.service import DatasetEmbedService
from app.llm.errors import LLMProviderError
from app.llm.schemas import ColumnExpansionResult
from app.shared.errors import ApiError


def make_upload_file(name: str, content: bytes) -> UploadFile:
    return UploadFile(filename=name, file=io.BytesIO(content))


class FakeVectorRepository:
    def __init__(self) -> None:
        self.create_called = False
        self.added_docs: list[Document] = []
        self.added_ids: list[str] = []
        self.deleted_listing_id: str | None = None
        self.deleted_ids: list[str] = []

    async def create_collection(self) -> None:
        self.create_called = True

    async def add_documents(self, docs, ids) -> None:
        self.added_docs = list(docs)
        self.added_ids = list(ids)

    async def delete_stale_documents(self, listing_id: str, ids: list[str]) -> None:
        self.deleted_listing_id = listing_id
        self.deleted_ids = list(ids)


class FakeLLMService:
    def __init__(self) -> None:
        self.expand_calls: list[tuple[list[str], list[list[str]]]] = []
        self.embedding_model = "llm-embedding-model"
        self.embedding_dimension = 384
        self.embeddings_client = object()

    async def expand_column_names(
        self, column_names: list[str], sample_rows: list[list[str]]
    ) -> ColumnExpansionResult:
        self.expand_calls.append((column_names, sample_rows))
        return ColumnExpansionResult(
            columns={col: f"{col} (expanded)" for col in column_names}
        )

    async def embed_text(self, text: str):
        raise AssertionError("DatasetEmbedService must not embed directly")

    async def embed_texts(self, texts: list[str]):
        raise AssertionError("DatasetEmbedService must not embed rows directly")


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
    vector_repository = overrides.pop("vector_repository", FakeVectorRepository())
    llm_service = overrides.pop("llm_service", FakeLLMService())
    repo = overrides.pop("repo", FakeKeyRepository())

    async def uploader(payload, filename, settings):
        return "ipfs://QmData", "0xdata"

    service = DatasetEmbedService(
        settings,
        llm_service=llm_service,
        vector_repository=vector_repository,
        session_factory=fake_session_factory,
        key_repository=repo,
        csv_loader_cls=overrides.pop("csv_loader_cls", FakeCSVLoader),
        key_generator=lambda: b"k" * 32,
        encryptor=lambda content, key, aad: (b"ciphertext", b"n" * 12),
        uploader=overrides.pop("uploader", uploader),
    )
    return SimpleNamespace(
        service=service,
        vector_repository=vector_repository,
        llm_service=llm_service,
        repo=repo,
    )


@pytest.mark.asyncio
async def test_embed_persists_row_documents(settings):
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
    assert response.vector_spec.model == settings.llm_embedding_model
    assert response.vector_spec.dimension == settings.llm_embedding_dimension

    repository = harness.vector_repository
    assert repository.create_called is True
    # One document per CSV data row (2 rows)
    assert len(repository.added_docs) == 2
    assert repository.added_ids == [
        f"{response.listing_id}:row:0",
        f"{response.listing_id}:row:1",
    ]
    assert repository.deleted_listing_id == response.listing_id
    assert repository.deleted_ids == repository.added_ids

    # Documents use LLM-expanded column names in page_content
    assert len(harness.llm_service.expand_calls) == 1
    expanded_cols, sample = harness.llm_service.expand_calls[0]
    assert expanded_cols == ["age", "cp"]

    for i, doc in enumerate(repository.added_docs):
        assert doc.metadata == {"listing_id": response.listing_id, "row_index": i}
        assert "age (expanded):" in doc.page_content
        assert "cp (expanded):" in doc.page_content

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
        "model": settings.llm_embedding_model,
        "dimension": settings.llm_embedding_dimension,
    }


@pytest.mark.asyncio
async def test_embed_respects_max_embed_rows(settings):
    one_row_settings = settings.model_copy(update={"max_embed_rows": 1})
    harness = make_service(one_row_settings)

    response = await harness.service.embed(
        file=make_upload_file("heart.csv", b"age,cp\n63,3\n37,2\n"),
        title="Heart",
        description="Cardio rows",
        seller="0x0000000000000000000000000000000000000001",
        price_atomic=100,
    )

    # Only 1 row document despite 2 CSV rows
    assert len(harness.vector_repository.added_docs) == 1
    assert harness.vector_repository.added_ids == [
        f"{response.listing_id}:row:0",
    ]


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
async def test_embed_does_not_write_key_when_vector_repository_fails(settings):
    vector_repository = FakeVectorRepository()

    async def fail_add(documents, ids):
        raise RuntimeError("vector repository down")

    vector_repository.add_documents = fail_add
    harness = make_service(settings, vector_repository=vector_repository)

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
async def test_embed_falls_back_to_raw_column_names_when_expand_fails(settings):
    class FailingExpandService(FakeLLMService):
        async def expand_column_names(self, column_names, sample_rows):
            raise LLMProviderError("OpenAI column expansion request failed")

    harness = make_service(settings, llm_service=FailingExpandService())

    # embed should still succeed — column expansion failure is a graceful fallback
    response = await harness.service.embed(
        file=make_upload_file("data.csv", b"age,cp\n63,3\n37,2\n"),
        title="Dataset",
        description="Desc",
        seller="0x0000000000000000000000000000000000000001",
        price_atomic=100,
    )

    assert response.dataset_url == "ipfs://QmData"
    # Raw column names used as fallback — page_content keeps original CSVLoader format
    docs = harness.vector_repository.added_docs
    assert len(docs) == 2
    assert "age:" in docs[0].page_content
    assert "cp:" in docs[0].page_content
    assert harness.repo.calls[0]["listing_id"] == response.listing_id


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
