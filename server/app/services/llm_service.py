import csv
import io
from functools import lru_cache
from typing import List, Tuple

from fastapi import HTTPException
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
        create_extension=False,
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


def parse_dataset_file(content: str) -> Tuple[List[List[str]], List[str], bool, int]:
    """Parse CSV file into records.

    Args:
        content (str): File content as string

    Returns:
        Tuple[List[List[str]], List[str], bool, int]: Parsed data rows, column names, has_header flag, empty rows skipped
    """

    csv_reader = csv.reader(io.StringIO(content))
    all_rows = list(csv_reader)

    if not all_rows:
        raise HTTPException(status_code=400, detail="File is empty")

    # Detect header by checking if first row is less numeric than second row
    has_header = False
    if len(all_rows) > 1:
        first_row = all_rows[0]
        second_row = all_rows[1]

        first_row_numeric = sum(
            1
            for val in first_row
            if val.replace(".", "", 1).replace("-", "", 1).isdigit()
        )
        second_row_numeric = sum(
            1
            for val in second_row
            if val.replace(".", "", 1).replace("-", "", 1).isdigit()
        )

        if (
            first_row_numeric < len(first_row) * 0.3
            and second_row_numeric > len(second_row) * 0.5
        ):
            has_header = True

    column_names: List[str] = []
    data_rows: List[List[str]] = []
    empty_rows_skipped = 0

    start_idx = 1 if has_header else 0

    if has_header:
        column_names = [str(val).strip() for val in all_rows[0]]

    for row in all_rows[start_idx:]:
        if not row or all(not str(val).strip() for val in row):
            empty_rows_skipped += 1
            continue
        data_rows.append([str(val).strip() for val in row])

    if not data_rows:
        raise HTTPException(status_code=400, detail="No valid data rows found in file")

    if not column_names:
        num_cols = len(data_rows[0]) if data_rows else 0
        column_names = [f"feature_{i}" for i in range(num_cols)]

    return data_rows, column_names, has_header, empty_rows_skipped


def record_to_text(
    record: List[str],
    column_names: List[str] | None = None,
) -> str:
    """Convert a dataset record to deterministic structured text.

    Uses a stable template format to ensure consistent text representation
    of tabular data for embedding generation.

    Args:
        record (List[str]): List of values in the record
        column_names (List[str] | None): Optional list of column names. If None, uses index-based naming.

    Returns:
        str: Deterministic text representation of the record
    """

    if not record:
        return ""

    if column_names is None:
        column_names = [f"col_{i}" for i in range(len(record))]

    if len(column_names) < len(record):
        column_names.extend([f"col_{i}" for i in range(len(column_names), len(record))])

    parts = []
    for col_name, value in zip(column_names, record):
        parts.append(f"{col_name}: {value}")

    return " | ".join(parts)


async def embed_query(
    text: str,
    settings: Settings,
) -> Tuple[List[float], int]:
    """Generate a query embedding using LangChain's Ollama integration.

    Args:
        text (str): Text to embed
        settings (Settings): Settings instance with embedding config

    Returns:
        Tuple[List[float], int]: Embedding vector and its dimension
    """

    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Text to embed cannot be empty")

    try:
        embedding = await get_embeddings(settings.embedding_model).aembed_query(text)
        return embedding, len(embedding)

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating embedding with Ollama: {str(exc)}",
        ) from exc
