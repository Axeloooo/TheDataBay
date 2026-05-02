import textwrap
from pathlib import Path

from pydantic_settings import SettingsError
import pytest
from pydantic import SecretStr, ValidationError

from app.config.settings import Settings, get_settings

ENV_TEMPLATE = """
APP_NAME="TheDataBay API"
APP_VERSION="0.1.0"
ENVIRONMENT="development"
HOST="localhost"
PORT="8080"
CORS_ORIGINS=["http://localhost:5173", "http://localhost:3000"]
LLM_PROVIDER="ollama"
LLM_BASE_URL="http://ollama-svc:11434"
LLM_CHAT_MODEL="deepseek-v4-flash:cloud"
LLM_EMBEDDING_MODEL="nomic-embed-text"
LLM_EMBEDDING_DIMENSION=768
LLM_THINK=false
OLLAMA_API_KEY="test-ollama-key"
DATASET_SUMMARY_COUNT=5
DATASET_SUMMARY_SAMPLE_ROWS=20
MAX_FILE_SIZE_MB=50
MAX_DATASET_ROWS=50000
TOP_K=10
SIMILARITY_THRESHOLD=0.5
CACHE_MAXSIZE=100
PINATA_API_KEY="k"
PINATA_SECRET_KEY="s"
PINATA_GATEWAY_URL="https://gateway.pinata.cloud"
CONTRACT_ADDRESS="0x0000000000000000000000000000000000000000"
PAYMENT_TOKEN_ADDRESS="0x0000000000000000000000000000000000000002"
CONTRACT_ABI_PATH="/tmp/Marketplace.json"
CHAIN_ID=31337
RPC_URL="http://127.0.0.1:8545"
SERVER_PRIVATE_KEY="0x1111111111111111111111111111111111111111111111111111111111111111"
POSTGRES_URL="postgresql+psycopg://user:password@localhost:5432/thedatabay"
"""


def write_env(tmp_path: Path, content: str = ENV_TEMPLATE) -> Path:
    env_path = tmp_path / ".env"
    env_path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")
    return env_path


def clear_relevant_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # Ensure no leakage from developer machine environment
    keys = [
        "APP_NAME",
        "APP_VERSION",
        "ENVIRONMENT",
        "HOST",
        "PORT",
        "CORS_ORIGINS",
        "LLM_PROVIDER",
        "LLM_BASE_URL",
        "LLM_CHAT_MODEL",
        "LLM_EMBEDDING_MODEL",
        "LLM_EMBEDDING_DIMENSION",
        "LLM_THINK",
        "OLLAMA_API_KEY",
        "DATASET_SUMMARY_COUNT",
        "DATASET_SUMMARY_SAMPLE_ROWS",
        "OLLAMA_HOST",
        "EMBEDDING_MODEL",
        "EMBEDDING_DIMENSION",
        "MAX_FILE_SIZE_MB",
        "MAX_DATASET_ROWS",
        "TOP_K",
        "SIMILARITY_THRESHOLD",
        "CACHE_MAXSIZE",
        "PINATA_API_KEY",
        "PINATA_SECRET_KEY",
        "PINATA_GATEWAY_URL",
        "CONTRACT_ADDRESS",
        "PAYMENT_TOKEN_ADDRESS",
        "CONTRACT_ABI_PATH",
        "CHAIN_ID",
        "RPC_URL",
        "SERVER_PRIVATE_KEY",
        "POSTGRES_URL",
    ]
    for k in keys:
        monkeypatch.delenv(k, raising=False)


def test_settings_loads_from_env_file(tmp_path, monkeypatch):
    clear_relevant_env(monkeypatch)
    env_file = write_env(tmp_path)

    s = Settings(_env_file=env_file)

    assert s.app_name == "TheDataBay API"
    assert s.app_version == "0.1.0"
    assert s.environment == "development"

    assert s.host == "localhost"
    assert s.port == 8080

    assert s.cors_origins == ["http://localhost:5173", "http://localhost:3000"]

    assert s.llm_provider == "ollama"
    assert s.llm_base_url == "http://ollama-svc:11434"
    assert s.llm_chat_model == "deepseek-v4-flash:cloud"
    assert s.llm_embedding_model == "nomic-embed-text"
    assert s.llm_embedding_dimension == 768
    assert s.llm_think is False
    assert isinstance(s.ollama_api_key, SecretStr)
    assert s.ollama_api_key.get_secret_value() == "test-ollama-key"
    assert s.dataset_summary_count == 5
    assert s.dataset_summary_sample_rows == 20

    assert s.max_file_size_mb == 50
    assert s.max_dataset_rows == 50000

    assert s.top_k == 10
    assert s.similarity_threshold == 0.5
    assert s.cache_maxsize == 100

    assert isinstance(s.pinata_api_key, SecretStr)
    assert isinstance(s.pinata_secret_key, SecretStr)
    assert s.pinata_api_key.get_secret_value() == "k"
    assert s.pinata_secret_key.get_secret_value() == "s"
    assert s.pinata_gateway_url == "https://gateway.pinata.cloud"
    assert s.contract_address == "0x0000000000000000000000000000000000000000"
    assert s.payment_token_address == "0x0000000000000000000000000000000000000002"
    assert s.contract_abi_path == "/tmp/Marketplace.json"
    assert s.chain_id == 31337
    assert s.rpc_url == "http://127.0.0.1:8545"
    assert isinstance(s.server_private_key, SecretStr)
    assert isinstance(s.database_url, SecretStr)
    assert (
        s.database_url.get_secret_value()
        == "postgresql+psycopg://user:password@localhost:5432/thedatabay"
    )


def test_settings_type_coercion(tmp_path, monkeypatch):
    clear_relevant_env(monkeypatch)
    env_file = write_env(
        tmp_path,
        """
        APP_NAME="TheDataBay API"
        APP_VERSION="0.1.0"
        ENVIRONMENT="development"
        HOST="0.0.0.0"
        PORT=8080
        CORS_ORIGINS=["http://a.com"]
        LLM_PROVIDER="ollama"
        LLM_BASE_URL="http://ollama:11434"
        LLM_CHAT_MODEL="deepseek-v4-flash:cloud"
        LLM_EMBEDDING_MODEL="m"
        LLM_EMBEDDING_DIMENSION="1024"
        LLM_THINK="true"
        DATASET_SUMMARY_COUNT="7"
        DATASET_SUMMARY_SAMPLE_ROWS="25"
        MAX_FILE_SIZE_MB="123"
        MAX_DATASET_ROWS="456"
        TOP_K="15"
        SIMILARITY_THRESHOLD="0.7"
        CACHE_MAXSIZE="150"
        PINATA_API_KEY="k"
        PINATA_SECRET_KEY="s"
        PINATA_GATEWAY_URL="https://gateway.pinata.cloud"
        CONTRACT_ADDRESS="0x0000000000000000000000000000000000000000"
        CONTRACT_ABI_PATH="/tmp/Marketplace.json"
        CHAIN_ID="31337"
        RPC_URL="http://127.0.0.1:8545"
        SERVER_PRIVATE_KEY="0x1111111111111111111111111111111111111111111111111111111111111111"
        POSTGRES_URL="postgresql+psycopg://user:password@localhost:5432/thedatabay"
        """,
    )

    s = Settings(_env_file=env_file)

    assert isinstance(s.port, int) and s.port == 8080
    assert s.llm_provider == "ollama"
    assert s.llm_base_url == "http://ollama:11434"
    assert s.llm_embedding_model == "m"
    assert (
        isinstance(s.llm_embedding_dimension, int) and s.llm_embedding_dimension == 1024
    )
    assert s.llm_think is True
    assert isinstance(s.dataset_summary_count, int) and s.dataset_summary_count == 7
    assert (
        isinstance(s.dataset_summary_sample_rows, int)
        and s.dataset_summary_sample_rows == 25
    )
    assert isinstance(s.max_file_size_mb, int) and s.max_file_size_mb == 123
    assert isinstance(s.max_dataset_rows, int) and s.max_dataset_rows == 456
    assert isinstance(s.top_k, int) and s.top_k == 15
    assert isinstance(s.similarity_threshold, float) and s.similarity_threshold == 0.7
    assert isinstance(s.cache_maxsize, int) and s.cache_maxsize == 150
    assert isinstance(s.cors_origins, list) and s.cors_origins == ["http://a.com"]
    assert isinstance(s.pinata_api_key, SecretStr)
    assert isinstance(s.pinata_secret_key, SecretStr)
    assert s.pinata_api_key.get_secret_value() == "k"
    assert s.pinata_secret_key.get_secret_value() == "s"
    assert isinstance(s.server_private_key, SecretStr)
    assert isinstance(s.database_url, SecretStr)


def test_env_vars_override_env_file(tmp_path, monkeypatch):
    clear_relevant_env(monkeypatch)
    env_file = write_env(tmp_path)

    # Override some fields via process env
    monkeypatch.setenv("APP_NAME", "Overridden Name")
    monkeypatch.setenv("PORT", "9999")
    monkeypatch.setenv("CORS_ORIGINS", '["http://override.local"]')

    s = Settings(_env_file=env_file)

    assert s.app_name == "Overridden Name"
    assert s.port == 9999
    assert s.cors_origins == ["http://override.local"]


def test_missing_required_vars_raises_validation_error(tmp_path, monkeypatch):
    clear_relevant_env(monkeypatch)

    # Missing a bunch of required keys
    env_file = write_env(
        tmp_path,
        """
        APP_NAME="TheDataBay API"
        APP_VERSION="0.1.0"
        """,
    )

    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=env_file)

    # Stronger assertions: ensure specific fields are reported missing
    msg = str(exc.value)
    assert "ENVIRONMENT" in msg or "environment" in msg
    assert "HOST" in msg or "host" in msg
    assert "PORT" in msg or "port" in msg
    assert "CORS_ORIGINS" in msg or "cors_origins" in msg
    assert "CONTRACT_ADDRESS" in msg or "contract_address" in msg
    assert "RPC_URL" in msg or "rpc_url" in msg
    assert "SERVER_PRIVATE_KEY" in msg or "server_private_key" in msg
    assert "DATABASE_URL" in msg or "POSTGRES_URL" in msg or "database_url" in msg


def test_invalid_cors_origins_format_raises(tmp_path, monkeypatch):
    clear_relevant_env(monkeypatch)

    # Not a JSON list; should fail to parse into list[str]
    env_file = write_env(
        tmp_path,
        """
        APP_NAME="TheDataBay API"
        APP_VERSION="0.1.0"
        ENVIRONMENT="development"
        HOST="localhost"
        PORT="8080"
        CORS_ORIGINS="http://localhost:5173,http://localhost:3000"
        MAX_FILE_SIZE_MB=50
        MAX_DATASET_ROWS=50000
        TOP_K=10
        SIMILARITY_THRESHOLD=0.5
        CACHE_MAXSIZE=100
        PINATA_API_KEY="k"
        PINATA_SECRET_KEY="s"
        PINATA_GATEWAY_URL="https://gateway.pinata.cloud"
        CONTRACT_ADDRESS="0x0000000000000000000000000000000000000000"
        CONTRACT_ABI_PATH="/tmp/Marketplace.json"
        CHAIN_ID=31337
        RPC_URL="http://127.0.0.1:8545"
        SERVER_PRIVATE_KEY="0x1111111111111111111111111111111111111111111111111111111111111111"
        POSTGRES_URL="postgresql+psycopg://user:password@localhost:5432/thedatabay"
        """,
    )

    with pytest.raises(SettingsError):
        Settings(_env_file=env_file)


def test_get_settings_cache_behavior(monkeypatch, tmp_path):
    """
    get_settings() is cached with @lru_cache. This test demonstrates that:
    - you must clear cache to reflect changes in environment
    """
    clear_relevant_env(monkeypatch)

    # Provide environment variables so Settings() can be constructed
    monkeypatch.setenv("APP_NAME", "Cached App")
    monkeypatch.setenv("APP_VERSION", "0.1.0")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("HOST", "localhost")
    monkeypatch.setenv("PORT", "8080")
    monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:5173"]')
    monkeypatch.setenv("MAX_FILE_SIZE_MB", "50")
    monkeypatch.setenv("MAX_DATASET_ROWS", "50000")
    monkeypatch.setenv("TOP_K", "10")
    monkeypatch.setenv("SIMILARITY_THRESHOLD", "0.5")
    monkeypatch.setenv("CACHE_MAXSIZE", "100")
    monkeypatch.setenv("PINATA_API_KEY", "k")
    monkeypatch.setenv("PINATA_SECRET_KEY", "s")
    monkeypatch.setenv("PINATA_GATEWAY_URL", "https://gateway.pinata.cloud")
    monkeypatch.setenv("CONTRACT_ADDRESS", "0x0000000000000000000000000000000000000000")
    monkeypatch.setenv("CONTRACT_ABI_PATH", "/tmp/Marketplace.json")
    monkeypatch.setenv("CHAIN_ID", "31337")
    monkeypatch.setenv("RPC_URL", "http://127.0.0.1:8545")
    monkeypatch.setenv(
        "SERVER_PRIVATE_KEY",
        "0x1111111111111111111111111111111111111111111111111111111111111111",
    )
    monkeypatch.setenv(
        "POSTGRES_URL",
        "postgresql+psycopg://user:password@localhost:5432/thedatabay",
    )

    get_settings.cache_clear()
    s1 = get_settings()
    assert s1.app_name == "Cached App"

    # Change env var after first call; cached instance should not change
    monkeypatch.setenv("APP_NAME", "Changed App")
    s2 = get_settings()
    assert s2 is s1
    assert s2.app_name == "Cached App"

    # After clearing cache, the new value should be picked up
    get_settings.cache_clear()
    s3 = get_settings()
    assert s3.app_name == "Changed App"


def test_legacy_ollama_and_embedding_env_names_are_migrated(tmp_path, monkeypatch):
    clear_relevant_env(monkeypatch)
    env_file = write_env(
        tmp_path,
        """
        APP_NAME="TheDataBay API"
        APP_VERSION="0.1.0"
        ENVIRONMENT="development"
        HOST="0.0.0.0"
        PORT=8080
        CORS_ORIGINS=["http://a.com"]
        OLLAMA_HOST="http://legacy-ollama:11434"
        EMBEDDING_MODEL="legacy-embed"
        EMBEDDING_DIMENSION="384"
        MAX_FILE_SIZE_MB="50"
        MAX_DATASET_ROWS="50000"
        TOP_K="10"
        SIMILARITY_THRESHOLD="0.7"
        CACHE_MAXSIZE="150"
        PINATA_API_KEY="k"
        PINATA_SECRET_KEY="s"
        PINATA_GATEWAY_URL="https://gateway.pinata.cloud"
        CONTRACT_ADDRESS="0x0000000000000000000000000000000000000000"
        CONTRACT_ABI_PATH="/tmp/Marketplace.json"
        CHAIN_ID="31337"
        RPC_URL="http://127.0.0.1:8545"
        SERVER_PRIVATE_KEY="0x1111111111111111111111111111111111111111111111111111111111111111"
        POSTGRES_URL="postgresql+psycopg://user:password@localhost:5432/thedatabay"
        """,
    )

    s = Settings(_env_file=env_file)

    assert s.llm_provider == "ollama"
    assert s.llm_base_url == "http://legacy-ollama:11434"
    assert s.llm_embedding_model == "legacy-embed"
    assert s.llm_embedding_dimension == 384
    assert s.llm_chat_model == "deepseek-v4-flash:cloud"
    assert s.llm_think is False
    assert s.dataset_summary_count == 5
    assert s.dataset_summary_sample_rows == 20
    assert s.ollama_api_key is None
