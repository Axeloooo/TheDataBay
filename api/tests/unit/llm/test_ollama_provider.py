import pytest
from pydantic import SecretStr

from app.config.settings import Settings
from app.llm.errors import LLMProviderError
from app.llm.providers.ollama import OllamaLLMService


class FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class FakeChatClient:
    def __init__(self, outputs: list[str]) -> None:
        self.outputs = outputs
        self.messages: list[object] = []

    async def ainvoke(self, messages: object) -> FakeMessage:
        self.messages.append(messages)
        return FakeMessage(self.outputs.pop(0))


class FakeEmbeddingsClient:
    def __init__(self) -> None:
        self.queries: list[str] = []
        self.documents: list[list[str]] = []

    async def aembed_query(self, text: str) -> list[float]:
        self.queries.append(text)
        return [0.1, 0.2, 0.3]

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        self.documents.append(texts)
        return [[float(index)] for index, _ in enumerate(texts)]


def make_settings(**overrides: object) -> Settings:
    data = {
        "APP_NAME": "TheDataBay API",
        "APP_VERSION": "0.1.0",
        "ENVIRONMENT": "test",
        "HOST": "localhost",
        "PORT": 8080,
        "CORS_ORIGINS": ["http://localhost:5173"],
        "LLM_PROVIDER": "ollama",
        "LLM_BASE_URL": "http://localhost:11434",
        "LLM_CHAT_MODEL": "deepseek-v4-flash:cloud",
        "LLM_EMBEDDING_MODEL": "nomic-embed-text",
        "LLM_EMBEDDING_DIMENSION": 768,
        "MAX_FILE_SIZE_MB": 50,
        "MAX_DATASET_ROWS": 50000,
        "TOP_K": 10,
        "SIMILARITY_THRESHOLD": None,
        "CACHE_MAXSIZE": 100,
        "PINATA_API_KEY": "k",
        "PINATA_SECRET_KEY": "s",
        "PINATA_GATEWAY_URL": "https://gateway.pinata.cloud",
        "CONTRACT_ADDRESS": "0x0000000000000000000000000000000000000000",
        "USDC_TOKEN_ADDRESS": "0x0000000000000000000000000000000000000002",
        "CONTRACT_ABI_PATH": "/tmp/Marketplace.json",
        "CHAIN_ID": 31337,
        "RPC_URL": "http://127.0.0.1:8545",
        "SERVER_PRIVATE_KEY": "0x" + "11" * 32,
        "POSTGRES_URL": "postgresql://user:password@localhost:5432/thedatabay",
    }
    data.update(overrides)
    return Settings(_env_file=None, **data)


def test_ollama_provider_uses_configured_model_defaults(monkeypatch):
    constructed = {}

    class FakeChat:
        def __init__(self, **kwargs) -> None:
            model = kwargs["model"]
            base_url = kwargs["base_url"]
            format = kwargs["format"]
            constructed["chat"] = {
                "model": model,
                "base_url": base_url,
                "format": format,
                "client_kwargs": kwargs["client_kwargs"],
                "async_client_kwargs": kwargs["async_client_kwargs"],
            }

    class FakeEmbeddings:
        def __init__(self, **kwargs) -> None:
            constructed["embeddings"] = kwargs

    monkeypatch.setattr("app.llm.providers.ollama.ChatOllama", FakeChat)
    monkeypatch.setattr(
        "app.llm.providers.ollama.OllamaEmbeddings", FakeEmbeddings
    )

    service = OllamaLLMService.from_settings(make_settings())

    assert service.chat_model == "deepseek-v4-flash:cloud"
    assert service.embedding_model == "nomic-embed-text"
    assert constructed == {
        "chat": {
            "model": "deepseek-v4-flash:cloud",
            "base_url": "http://localhost:11434",
            "format": "json",
            "client_kwargs": {},
            "async_client_kwargs": {},
        },
        "embeddings": {
            "model": "nomic-embed-text",
            "base_url": "http://localhost:11434",
            "client_kwargs": {},
            "async_client_kwargs": {},
        },
    }
    assert service.embeddings_client is not None


def test_ollama_provider_passes_optional_api_key_as_bearer_header(monkeypatch):
    constructed = {}

    class FakeChat:
        def __init__(self, **kwargs) -> None:
            constructed["chat"] = kwargs

    class FakeEmbeddings:
        def __init__(self, **kwargs) -> None:
            constructed["embeddings"] = kwargs

    monkeypatch.setattr("app.llm.providers.ollama.ChatOllama", FakeChat)
    monkeypatch.setattr(
        "app.llm.providers.ollama.OllamaEmbeddings", FakeEmbeddings
    )

    OllamaLLMService.from_settings(make_settings(OLLAMA_API_KEY="secret-token"))

    expected = {"headers": {"Authorization": "Bearer secret-token"}}
    assert constructed["chat"]["client_kwargs"] == expected
    assert constructed["chat"]["async_client_kwargs"] == expected
    assert constructed["embeddings"]["client_kwargs"] == expected
    assert constructed["embeddings"]["async_client_kwargs"] == expected


def test_ollama_provider_rejects_hosted_endpoint_without_api_key():
    settings = make_settings(
        LLM_BASE_URL="https://ollama.example.test",
        OLLAMA_API_KEY=None,
    )

    with pytest.raises(LLMProviderError, match="OLLAMA_API_KEY"):
        OllamaLLMService.from_settings(settings)


def test_ollama_provider_allows_hosted_endpoint_with_api_key(monkeypatch):
    constructed = {}

    class FakeChat:
        def __init__(self, **kwargs) -> None:
            constructed["chat"] = kwargs

    class FakeEmbeddings:
        def __init__(self, **kwargs) -> None:
            constructed["embeddings"] = kwargs

    monkeypatch.setattr("app.llm.providers.ollama.ChatOllama", FakeChat)
    monkeypatch.setattr(
        "app.llm.providers.ollama.OllamaEmbeddings", FakeEmbeddings
    )

    settings = make_settings(
        LLM_BASE_URL="https://ollama.example.test",
        OLLAMA_API_KEY=SecretStr("secret-token"),
    )

    OllamaLLMService.from_settings(settings)

    assert constructed["chat"]["base_url"] == "https://ollama.example.test"


async def test_embed_text_returns_vector_with_model_metadata():
    embeddings = FakeEmbeddingsClient()
    service = OllamaLLMService(
        chat_client=FakeChatClient([]),
        embeddings_client=embeddings,
        chat_model="chat-model",
        embedding_model="embedding-model",
    )

    result = await service.embed_text("climate rows")

    assert embeddings.queries == ["climate rows"]
    assert result.vector == [0.1, 0.2, 0.3]
    assert result.model == "embedding-model"
    assert result.dimension == 3


async def test_embed_texts_returns_batch_vectors():
    embeddings = FakeEmbeddingsClient()
    service = OllamaLLMService(
        chat_client=FakeChatClient([]),
        embeddings_client=embeddings,
        chat_model="chat-model",
        embedding_model="embedding-model",
    )

    result = await service.embed_texts(["alpha", "beta"])

    assert embeddings.documents == [["alpha", "beta"]]
    assert result.model == "embedding-model"
    assert result.embeddings[0].vector == [0.0]
    assert result.embeddings[1].vector == [1.0]
