"""
Configuration management using pydantic-settings for environment-based configuration.
"""

from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application configuration with environment variable support."""

    # App settings
    app_name: str = Field(alias="APP_NAME")
    app_version: str = Field(alias="APP_VERSION")
    environment: str = Field(alias="ENVIRONMENT")

    # Server settings
    host: str = Field(alias="HOST")
    port: int = Field(alias="PORT")

    # CORS settings
    cors_origins: list[str] = Field(alias="CORS_ORIGINS")

    # Ollama settings
    embedding_model: str = Field(alias="EMBEDDING_MODEL")

    # Embedding job settings
    max_file_size_mb: int = Field(alias="MAX_FILE_SIZE_MB")
    max_dataset_rows: int = Field(alias="MAX_DATASET_ROWS")
    embedding_chunk_size: int = Field(alias="EMBEDDING_CHUNK_SIZE")

    # Pinata IPFS settings
    pinata_api_key: str = Field(alias="PINATA_API_KEY")
    pinata_secret_key: str = Field(alias="PINATA_SECRET_KEY")
    pinata_gateway_url: str = Field(alias="PINATA_GATEWAY_URL")

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        Settings: The application settings.
    """
    return Settings()
