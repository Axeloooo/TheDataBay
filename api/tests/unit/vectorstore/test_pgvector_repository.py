from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from langchain_core.documents import Document

from app.vectorstore.repositories.pgvector_repository import (
    DATASET_SUMMARIES_COLLECTION,
    PGVectorRepository,
    pgvector_repository_for_settings,
)


class FakePGVector:
    instances: list["FakePGVector"] = []

    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.acreate_collection = AsyncMock()
        self.aadd_documents = AsyncMock()
        self.asimilarity_search_with_score_by_vector = AsyncMock(
            return_value=[(Document(page_content="summary"), 0.25)]
        )
        self.instances.append(self)


class FakeEmbeddings:
    pass


class FakeSession:
    def __init__(self) -> None:
        self.executed = []

    def begin(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, statement, params):
        self.executed.append((str(statement), params))


class FakeSessionFactory:
    def __init__(self) -> None:
        self.session = FakeSession()

    def __call__(self) -> FakeSession:
        return self.session


@pytest.fixture(autouse=True)
def reset_fakes():
    FakePGVector.instances = []


def make_repository(**overrides) -> PGVectorRepository:
    params = {
        "connection": "postgresql+psycopg://user:pass@localhost:5432/db",
        "embeddings": FakeEmbeddings(),
        "embedding_dimension": 768,
        "pgvector_cls": FakePGVector,
    }
    params.update(overrides)
    return PGVectorRepository(**params)


def test_repository_can_be_created_from_settings():
    settings = SimpleNamespace(
        psycopg_database_url="postgresql+psycopg://user:pass@localhost:5432/db",
        llm_embedding_dimension=768,
    )

    repository = pgvector_repository_for_settings(
        settings,
        embeddings=FakeEmbeddings(),
        session_factory=FakeSessionFactory(),
        pgvector_cls=FakePGVector,
    )

    assert isinstance(repository, PGVectorRepository)


def test_collection_targets_dataset_summaries_not_legacy_rows():
    assert DATASET_SUMMARIES_COLLECTION == "dataset_summaries"
    assert DATASET_SUMMARIES_COLLECTION != "dataset_rows"


@pytest.mark.asyncio
async def test_create_collection_and_add_documents_use_dataset_summaries_collection():
    repository = make_repository()
    docs = [Document(page_content="Heart dataset summary", metadata={"listing_id": "l1"})]

    assert FakePGVector.instances == []

    await repository.create_collection()
    await repository.add_documents(docs, ids=["l1:summary"])

    assert len(FakePGVector.instances) == 1
    vectorstore = FakePGVector.instances[0]
    assert isinstance(vectorstore.kwargs["embeddings"], FakeEmbeddings)
    assert vectorstore.kwargs == {
        "embeddings": vectorstore.kwargs["embeddings"],
        "collection_name": DATASET_SUMMARIES_COLLECTION,
        "connection": "postgresql+psycopg://user:pass@localhost:5432/db",
        "embedding_length": 768,
        "use_jsonb": True,
        "create_extension": True,
        "async_mode": True,
    }
    vectorstore.acreate_collection.assert_awaited_once_with()
    vectorstore.aadd_documents.assert_awaited_once_with(docs, ids=["l1:summary"])


def test_repository_factory_rejects_missing_llm_embedding_client():
    settings = SimpleNamespace(
        psycopg_database_url="postgresql+psycopg://user:pass@localhost:5432/db",
        llm_embedding_dimension=768,
    )

    with pytest.raises(RuntimeError, match="llm domain"):
        pgvector_repository_for_settings(settings)


@pytest.mark.asyncio
async def test_similarity_search_by_vector_delegates_to_scored_pgvector_search():
    repository = make_repository()

    hits = await repository.similarity_search_by_vector([0.1, 0.2], k=5)

    assert hits == [(Document(page_content="summary"), 0.75)]
    FakePGVector.instances[0].asimilarity_search_with_score_by_vector.assert_awaited_once_with(
        [0.1, 0.2],
        k=5,
    )


@pytest.mark.asyncio
async def test_delete_stale_documents_removes_listing_docs_outside_current_ids():
    session_factory = FakeSessionFactory()
    repository = make_repository(session_factory=session_factory)

    await repository.delete_stale_documents(
        listing_id="listing-1",
        current_ids=["listing-1:summary"],
    )

    assert len(session_factory.session.executed) == 1
    statement, params = session_factory.session.executed[0]
    assert "DELETE FROM langchain_pg_embedding" in statement
    assert "langchain_pg_collection" in statement
    assert "c.name = :collection_name" in statement
    assert "e.cmetadata->>'listing_id' = :listing_id" in statement
    assert "e.id != ALL(:current_ids)" in statement
    assert params == {
        "collection_name": DATASET_SUMMARIES_COLLECTION,
        "listing_id": "listing-1",
        "current_ids": ["listing-1:summary"],
    }


@pytest.mark.asyncio
async def test_feature_services_can_call_repository_methods_without_pgvector_client():
    repository = SimpleNamespace(
        create_collection=AsyncMock(),
        add_documents=AsyncMock(),
        similarity_search_by_vector=AsyncMock(return_value=[]),
        delete_stale_documents=AsyncMock(),
    )

    async def dataset_feature_service(vector_repository):
        docs = [Document(page_content="Dataset summary", metadata={"listing_id": "l1"})]
        ids = ["l1:summary"]
        await vector_repository.create_collection()
        await vector_repository.add_documents(docs, ids=ids)
        await vector_repository.delete_stale_documents("l1", ids)

    async def ai_feature_service(vector_repository):
        return await vector_repository.similarity_search_by_vector([0.3, 0.4], k=10)

    await dataset_feature_service(repository)
    await ai_feature_service(repository)

    repository.create_collection.assert_awaited_once_with()
    repository.add_documents.assert_awaited_once()
    repository.delete_stale_documents.assert_awaited_once_with("l1", ["l1:summary"])
    repository.similarity_search_by_vector.assert_awaited_once_with([0.3, 0.4], k=10)
