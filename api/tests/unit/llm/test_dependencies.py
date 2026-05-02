from app.config.settings import Settings
from app.llm.dependencies import get_llm_service
from app.llm.services.ollama_provider import OllamaLLMService


def make_settings(**overrides: object) -> Settings:
    data = {
        "APP_NAME": "TheDataBay API",
        "APP_VERSION": "0.1.0",
        "ENVIRONMENT": "test",
        "HOST": "localhost",
        "PORT": 8080,
        "CORS_ORIGINS": ["http://localhost:5173"],
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


def test_get_llm_service_returns_ollama_provider(monkeypatch):
    calls = []

    def fake_from_settings(settings: Settings) -> OllamaLLMService:
        calls.append(settings)
        return object()  # type: ignore[return-value]

    monkeypatch.setattr(OllamaLLMService, "from_settings", fake_from_settings)

    settings = make_settings()
    service = get_llm_service(settings)

    assert service is not None
    assert calls == [settings]
