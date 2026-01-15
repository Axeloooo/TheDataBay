"""
Configuration management using pydantic-settings for environment-based configuration.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration with environment variable support."""

    # App settings
    app_name: str = "BridgeMart API"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS settings
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Ollama settings
    ollama_host: str = "http://localhost:11434"
    embedding_model: str = "nomic-embed-text"
    thinking_model: str = "llama3.2:latest"

    # Embedding job settings
    max_file_size_mb: int = 50
    max_dataset_rows: int = 50000
    embedding_chunk_size: int = 256

    # Pinata IPFS settings
    pinata_api_key: str = ""
    pinata_secret_key: str = ""
    pinata_gateway_url: str = "https://gateway.pinata.cloud"

    # AI/ML settings
    pytorch_device: str = "cpu"  # or "cuda" if GPU available
    similarity_threshold: float = 0.7

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )


# Global settings instance
settings = Settings()
