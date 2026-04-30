import pytest
from fastapi import HTTPException

from app.ai import service as ai_service
from app.shared import vectorstore as llm_service


def test_warmup_model_success(monkeypatch, settings):
    class FakeEmbeddings:
        def embed_query(self, text):
            self.text = text
            return [0.1] * settings.embedding_dimension

    fake = FakeEmbeddings()
    monkeypatch.setattr(llm_service, "get_embeddings", lambda model, base_url: fake)

    assert llm_service.warmup_model(settings) is True
    assert fake.text == "warmup"


def test_warmup_model_failure(monkeypatch, settings):
    class FakeEmbeddings:
        def embed_query(self, text):
            raise RuntimeError("boom")

    monkeypatch.setattr(
        llm_service, "get_embeddings", lambda model, base_url: FakeEmbeddings()
    )

    assert llm_service.warmup_model(settings) is False


def test_get_vectorstore_creates_pgvector_extension(monkeypatch):
    captured = {}

    class FakePGVector:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(llm_service, "PGVector", FakePGVector)
    monkeypatch.setattr(llm_service, "get_embeddings", lambda model, base_url: object())

    llm_service.get_vectorstore(
        "postgresql+psycopg://db", "nomic", "http://ollama:11434", 768
    )

    assert captured["create_extension"] is True
    assert captured["embeddings"] is not None


def test_get_embeddings_passes_ollama_base_url(monkeypatch):
    captured = {}

    class FakeOllamaEmbeddings:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(llm_service, "OllamaEmbeddings", FakeOllamaEmbeddings)

    llm_service.get_embeddings("nomic-embed-text", "http://ollama-svc:11434")

    assert captured == {
        "model": "nomic-embed-text",
        "base_url": "http://ollama-svc:11434",
    }


@pytest.mark.asyncio
async def test_embed_query_success(monkeypatch, settings):
    class FakeEmbeddings:
        async def aembed_query(self, text):
            assert text == "hello"
            return [0.1, 0.2, 0.3]

    monkeypatch.setattr(
        ai_service, "get_embeddings", lambda model, base_url: FakeEmbeddings()
    )

    embedding, dim = await ai_service.embed_query("hello", settings)
    assert embedding == [0.1, 0.2, 0.3]
    assert dim == 3


def test_embed_query_empty_raises(settings):
    with pytest.raises(HTTPException):
        import asyncio

        asyncio.run(ai_service.embed_query("   ", settings))
