from functools import lru_cache

from langchain_ollama import OllamaEmbeddings
from langchain_postgres import PGVector

from ..config.settings import Settings

DATASET_ROWS_COLLECTION = "dataset_rows"


@lru_cache(maxsize=32)
def get_embeddings(model: str) -> OllamaEmbeddings:
    """Return a cached LangChain Ollama embeddings client for a model."""
    return OllamaEmbeddings(model=model)


@lru_cache(maxsize=32)
def get_vectorstore(connection: str, model: str, embedding_dimension: int) -> PGVector:
    """Return a cached async LangChain PGVector store for dataset rows."""
    return PGVector(
        embeddings=get_embeddings(model),
        collection_name=DATASET_ROWS_COLLECTION,
        connection=connection,
        embedding_length=embedding_dimension,
        use_jsonb=True,
        create_extension=True,
        async_mode=True,
    )


def vectorstore_for_settings(settings: Settings) -> PGVector:
    """Resolve the configured PGVector store."""
    return get_vectorstore(
        settings.psycopg_database_url,
        settings.embedding_model,
        settings.embedding_dimension,
    )


def warmup_model(settings: Settings) -> bool:
    """Warm up the embedding model on startup.

    Args:
        settings (Settings): Application settings instance

    Returns:
        bool: True if warmup succeeded, False otherwise
    """

    try:
        vector = get_embeddings(settings.embedding_model).embed_query("warmup")
        actual_dim = len(vector)
        if actual_dim != settings.embedding_dimension:
            raise ValueError(
                f"Embedding dimension mismatch: model '{settings.embedding_model}' "
                f"returned {actual_dim} dimensions but EMBEDDING_DIMENSION is set to "
                f"{settings.embedding_dimension}. Update EMBEDDING_DIMENSION in your "
                f"environment to match the model output."
            )
        return True
    except Exception as exc:
        print(f"Warning: Model warmup failed: {str(exc)}")
        return False
