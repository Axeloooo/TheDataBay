"""
Configuration management using pydantic-settings for environment-based configuration.
"""

from functools import lru_cache
from pathlib import Path
from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]   # api/
REPO_ROOT = BASE_DIR.parent                       # monorepo root


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

    # LLM settings
    llm_provider: str = Field(default="ollama", alias="LLM_PROVIDER")
    # OLLAMA_HOST is a legacy alias kept for backward compatibility
    llm_base_url: str = Field(
        default="http://localhost:11434",
        validation_alias=AliasChoices("LLM_BASE_URL", "OLLAMA_HOST"),
    )
    # When absent, OllamaLLMService falls back to llm_base_url so a single
    # LLM_BASE_URL setting covers both chat and embeddings in Kubernetes.
    llm_embedding_base_url: str | None = Field(default=None, alias="LLM_EMBEDDING_BASE_URL")
    # Defaults match the Ollama provider (LLM_PROVIDER default is "ollama")
    llm_chat_model: str = Field(default="deepseek-v4-flash:cloud", alias="LLM_CHAT_MODEL")
    # EMBEDDING_MODEL is a legacy alias kept for backward compatibility
    llm_embedding_model: str = Field(
        default="nomic-embed-text",
        validation_alias=AliasChoices("LLM_EMBEDDING_MODEL", "EMBEDDING_MODEL"),
    )
    # EMBEDDING_DIMENSION is a legacy alias kept for backward compatibility
    llm_embedding_dimension: int = Field(
        default=768,
        validation_alias=AliasChoices("LLM_EMBEDDING_DIMENSION", "EMBEDDING_DIMENSION"),
    )
    llm_think: bool = Field(default=False, alias="LLM_THINK")
    ollama_api_key: SecretStr | None = Field(default=None, alias="OLLAMA_API_KEY")
    openai_api_key: SecretStr | None = Field(default=None, alias="OPENAI_API_KEY")

    # Embedding job settings
    max_file_size_mb: int = Field(alias="MAX_FILE_SIZE_MB")
    max_dataset_rows: int = Field(alias="MAX_DATASET_ROWS")
    max_embed_rows: int = Field(default=2000, alias="MAX_EMBED_ROWS")

    # Similarity search settings
    top_k: int = Field(alias="TOP_K")
    similarity_threshold: float | None = Field(alias="SIMILARITY_THRESHOLD")
    cache_maxsize: int = Field(alias="CACHE_MAXSIZE")

    # Pinata IPFS settings
    pinata_api_key: SecretStr = Field(alias="PINATA_API_KEY")
    pinata_secret_key: SecretStr = Field(alias="PINATA_SECRET_KEY")
    pinata_gateway_url: str = Field(alias="PINATA_GATEWAY_URL")

    # Smart contract settings
    contract_address: str = Field(alias="CONTRACT_ADDRESS")
    usdc_token_address: str = Field(default="", alias="USDC_TOKEN_ADDRESS")
    cadc_token_address: str = Field(default="", alias="CADC_TOKEN_ADDRESS")
    contract_abi_path: str = Field(alias="CONTRACT_ABI_PATH")
    chain_id: int = Field(alias="CHAIN_ID")
    rpc_url: str = Field(alias="RPC_URL")
    server_private_key: SecretStr = Field(alias="SERVER_PRIVATE_KEY")

    # Database settings
    database_url: SecretStr = Field(alias="POSTGRES_URL")

    @property
    def chat_model(self) -> str:
        """Return the configured chat model."""
        return self.llm_chat_model

    @property
    def async_database_url(self) -> str:
        """Return a postgresql+asyncpg:// URL for async SQLAlchemy usage."""
        url = self.database_url.get_secret_value()
        driver_aliases = {
            "postgresql+psycopg3://": "postgresql+asyncpg://",
            "postgresql+psycopg2://": "postgresql+asyncpg://",
            "postgresql+psycopg://": "postgresql+asyncpg://",
            "postgresql://": "postgresql+asyncpg://",
            "postgres://": "postgresql+asyncpg://",
        }

        for prefix, async_prefix in driver_aliases.items():
            if url.startswith(prefix):
                return url.replace(prefix, async_prefix, 1)
        return url

    @property
    def psycopg_database_url(self) -> str:
        """Return a psycopg3 URL for LangChain's PGVector integration."""
        url = self.database_url.get_secret_value()
        driver_aliases = {
            "postgresql+asyncpg://": "postgresql+psycopg://",
            "postgresql+psycopg2://": "postgresql+psycopg://",
            "postgresql+psycopg3://": "postgresql+psycopg://",
            "postgresql://": "postgresql+psycopg://",
            "postgres://": "postgresql+psycopg://",
        }

        for prefix, psycopg_prefix in driver_aliases.items():
            if url.startswith(prefix):
                return url.replace(prefix, psycopg_prefix, 1)
        return url

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        Settings: The application settings.
    """
    return Settings()
