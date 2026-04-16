import asyncio

import pytest
from fastapi import HTTPException

from app.services import llm_service


class DummyEmbedResponse:
    def __init__(self, embeddings):
        self.embeddings = embeddings


def test_warmup_model_success(monkeypatch, settings):
    called = {}

    def fake_embed(model, input):
        called["model"] = model
        called["input"] = input
        return None

    monkeypatch.setattr(llm_service.ollama, "embed", fake_embed)

    assert llm_service.warmup_model(settings) is True
    assert called["model"] == settings.embedding_model
    assert called["input"] == "warmup test"


def test_warmup_model_failure(monkeypatch, settings):
    def fake_embed(model, input):
        raise RuntimeError("boom")

    monkeypatch.setattr(llm_service.ollama, "embed", fake_embed)

    assert llm_service.warmup_model(settings) is False


def test_parse_dataset_file_with_header():
    content = "col1,col2\n1,2\n3,4\n"
    rows, cols, has_header, skipped = llm_service.parse_dataset_file(content)

    assert has_header is True
    assert cols == ["col1", "col2"]
    assert rows == [["1", "2"], ["3", "4"]]
    assert skipped == 0


def test_parse_dataset_file_without_header():
    content = "1,2\n3,4\n"
    rows, cols, has_header, skipped = llm_service.parse_dataset_file(content)

    assert has_header is False
    assert cols == ["feature_0", "feature_1"]
    assert rows == [["1", "2"], ["3", "4"]]
    assert skipped == 0


def test_parse_dataset_file_empty():
    with pytest.raises(HTTPException):
        llm_service.parse_dataset_file("")


def test_record_to_text_extends_columns():
    text = llm_service.record_to_text(["a", "b"], ["x"])
    assert text == "x: a | col_1: b"


def test_generate_single_embedding_success(monkeypatch, settings):
    def fake_embed(model, input):
        return DummyEmbedResponse([[0.1, 0.2, 0.3]])

    monkeypatch.setattr(llm_service.ollama, "embed", fake_embed)

    embedding, dim = llm_service.generate_single_embedding("hello", settings)
    assert embedding == [0.1, 0.2, 0.3]
    assert dim == 3


def test_generate_single_embedding_empty_raises(settings):
    with pytest.raises(HTTPException):
        llm_service.generate_single_embedding("   ", settings)


def test_generate_embeddings_chunked(monkeypatch, settings):
    async def fake_sleep(_):
        return None

    def fake_embed(model, input):
        return DummyEmbedResponse(
            [[float(i), float(i) + 1.0] for i in range(len(input))]
        )

    monkeypatch.setattr(llm_service.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(llm_service.ollama, "embed", fake_embed)

    texts = ["a", "b", "c"]
    embeddings, dim = asyncio.run(
        llm_service.generate_embeddings_chunked(texts, settings, chunk_size=2)
    )

    assert len(embeddings) == 3
    assert dim == 2


def test_generate_embeddings_chunked_error(monkeypatch, settings):
    def fake_embed(model, input):
        raise RuntimeError("boom")

    monkeypatch.setattr(llm_service.ollama, "embed", fake_embed)

    with pytest.raises(HTTPException):
        asyncio.run(llm_service.generate_embeddings_chunked(["a"], settings))


# ---------------------------------------------------------------------------
# mean_pool tests
# ---------------------------------------------------------------------------


def test_mean_pool_single_embedding_returns_same_vector():
    result = llm_service.mean_pool([[1.0, 2.0, 3.0]])
    assert result == [1.0, 2.0, 3.0]


def test_mean_pool_two_identical_embeddings_returns_same_vector():
    result = llm_service.mean_pool([[1.0, 0.0], [1.0, 0.0]])
    assert result == [1.0, 0.0]


def test_mean_pool_two_opposite_embeddings_returns_zero_vector():
    result = llm_service.mean_pool([[1.0, -1.0], [-1.0, 1.0]])
    assert result == [0.0, 0.0]


def test_mean_pool_empty_list_raises_value_error():
    with pytest.raises(ValueError):
        llm_service.mean_pool([])


def test_mean_pool_mismatched_dimensions_raises_value_error():
    with pytest.raises(ValueError):
        llm_service.mean_pool([[1.0, 2.0], [3.0]])
