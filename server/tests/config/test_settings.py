import textwrap
from pathlib import Path

from pydantic_settings import SettingsError
import pytest
from pydantic import SecretStr, ValidationError

from app.config.settings import Settings, get_settings


ENV_TEMPLATE = """
APP_NAME="BridgeMart API"
APP_VERSION="0.1.0"
ENVIRONMENT="development"
HOST="localhost"
PORT="8080"
CORS_ORIGINS=["http://localhost:5173", "http://localhost:3000"]
EMBEDDING_MODEL="nomic-embed-text"
MAX_FILE_SIZE_MB=50
MAX_DATASET_ROWS=50000
EMBEDDING_CHUNK_SIZE=256
PINATA_API_KEY="k"
PINATA_SECRET_KEY="s"
PINATA_GATEWAY_URL="https://gateway.pinata.cloud"
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
        "EMBEDDING_MODEL",
        "MAX_FILE_SIZE_MB",
        "MAX_DATASET_ROWS",
        "EMBEDDING_CHUNK_SIZE",
        "PINATA_API_KEY",
        "PINATA_SECRET_KEY",
        "PINATA_GATEWAY_URL",
    ]
    for k in keys:
        monkeypatch.delenv(k, raising=False)


def test_settings_loads_from_env_file(tmp_path, monkeypatch):
    clear_relevant_env(monkeypatch)
    env_file = write_env(tmp_path)

    s = Settings(_env_file=env_file)

    assert s.app_name == "BridgeMart API"
    assert s.app_version == "0.1.0"
    assert s.environment == "development"

    assert s.host == "localhost"
    assert s.port == 8080

    assert s.cors_origins == ["http://localhost:5173", "http://localhost:3000"]

    assert s.embedding_model == "nomic-embed-text"

    assert s.max_file_size_mb == 50
    assert s.max_dataset_rows == 50000
    assert s.embedding_chunk_size == 256

    # fix as both keys as SecretStr
    assert isinstance(s.pinata_api_key, SecretStr)
    assert isinstance(s.pinata_secret_key, SecretStr)
    assert s.pinata_api_key.get_secret_value() == "k"
    assert s.pinata_secret_key.get_secret_value() == "s"
    assert s.pinata_gateway_url == "https://gateway.pinata.cloud"


def test_settings_type_coercion(tmp_path, monkeypatch):
    clear_relevant_env(monkeypatch)
    env_file = write_env(
        tmp_path,
        """
        APP_NAME="BridgeMart API"
        APP_VERSION="0.1.0"
        ENVIRONMENT="development"
        HOST="0.0.0.0"
        PORT=8080
        CORS_ORIGINS=["http://a.com"]
        EMBEDDING_MODEL="m"
        MAX_FILE_SIZE_MB="123"
        MAX_DATASET_ROWS="456"
        EMBEDDING_CHUNK_SIZE="789"
        PINATA_API_KEY="k"
        PINATA_SECRET_KEY="s"
        PINATA_GATEWAY_URL="https://gateway.pinata.cloud"
        """,
    )

    s = Settings(_env_file=env_file)

    assert isinstance(s.port, int) and s.port == 8080
    assert isinstance(s.max_file_size_mb, int) and s.max_file_size_mb == 123
    assert isinstance(s.max_dataset_rows, int) and s.max_dataset_rows == 456
    assert isinstance(s.embedding_chunk_size, int) and s.embedding_chunk_size == 789
    assert isinstance(s.cors_origins, list) and s.cors_origins == ["http://a.com"]
    assert isinstance(s.pinata_api_key, SecretStr)
    assert isinstance(s.pinata_secret_key, SecretStr)
    assert s.pinata_api_key.get_secret_value() == "k"
    assert s.pinata_secret_key.get_secret_value() == "s"


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
        APP_NAME="BridgeMart API"
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


def test_invalid_cors_origins_format_raises(tmp_path, monkeypatch):
    clear_relevant_env(monkeypatch)

    # Not a JSON list; should fail to parse into list[str]
    env_file = write_env(
        tmp_path,
        """
        APP_NAME="BridgeMart API"
        APP_VERSION="0.1.0"
        ENVIRONMENT="development"
        HOST="localhost"
        PORT="8080"
        CORS_ORIGINS="http://localhost:5173,http://localhost:3000"
        EMBEDDING_MODEL="nomic-embed-text"
        MAX_FILE_SIZE_MB=50
        MAX_DATASET_ROWS=50000
        EMBEDDING_CHUNK_SIZE=256
        PINATA_API_KEY="k"
        PINATA_SECRET_KEY="s"
        PINATA_GATEWAY_URL="https://gateway.pinata.cloud"
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
    monkeypatch.setenv("EMBEDDING_MODEL", "m")
    monkeypatch.setenv("MAX_FILE_SIZE_MB", "50")
    monkeypatch.setenv("MAX_DATASET_ROWS", "50000")
    monkeypatch.setenv("EMBEDDING_CHUNK_SIZE", "256")
    monkeypatch.setenv("PINATA_API_KEY", "k")
    monkeypatch.setenv("PINATA_SECRET_KEY", "s")
    monkeypatch.setenv("PINATA_GATEWAY_URL", "https://gateway.pinata.cloud")

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
