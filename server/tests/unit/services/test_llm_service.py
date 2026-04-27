import pytest
from fastapi import HTTPException

from app.services import llm_service


def test_warmup_model_success(monkeypatch, settings):
    class FakeEmbeddings:
        def embed_query(self, text):
            self.text = text
            return [0.1, 0.2]

    fake = FakeEmbeddings()
    monkeypatch.setattr(llm_service, "get_embeddings", lambda model: fake)

    assert llm_service.warmup_model(settings) is True
    assert fake.text == "warmup"


def test_warmup_model_failure(monkeypatch, settings):
    class FakeEmbeddings:
        def embed_query(self, text):
            raise RuntimeError("boom")

    monkeypatch.setattr(llm_service, "get_embeddings", lambda model: FakeEmbeddings())

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



@pytest.mark.asyncio
async def test_embed_query_success(monkeypatch, settings):
    class FakeEmbeddings:
        async def aembed_query(self, text):
            assert text == "hello"
            return [0.1, 0.2, 0.3]

    monkeypatch.setattr(llm_service, "get_embeddings", lambda model: FakeEmbeddings())

    embedding, dim = await llm_service.embed_query("hello", settings)
    assert embedding == [0.1, 0.2, 0.3]
    assert dim == 3


def test_embed_query_empty_raises(settings):
    with pytest.raises(HTTPException):
        import asyncio

        asyncio.run(llm_service.embed_query("   ", settings))
