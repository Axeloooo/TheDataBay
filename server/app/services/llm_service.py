"""
LLM service functions for embedding generation using Ollama.
"""

import csv
import io
import asyncio
from typing import List, Tuple

import ollama
from ollama import EmbedResponse
from fastapi import HTTPException

from ..config.settings import Settings


def warmup_model(settings: Settings) -> bool:
    """Warm up the embedding model on startup.

    Args:
        settings (Settings): Application settings instance

    Returns:
        bool: True if warmup succeeded, False otherwise
    """
    try:
        test_text = "warmup test"
        ollama.embed(model=settings.embedding_model, input=test_text)
        return True
    except Exception as exc:
        print(f"Warning: Model warmup failed: {str(exc)}")
        return False


def parse_dataset_file(content: str) -> Tuple[List[List[str]], List[str], bool, int]:
    """Parse CSV file into records.

    Args:
        content (str): File content as string
        filename (str): Original filename

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


async def generate_embeddings_chunked(
    texts: List[str],
    settings: Settings,
    chunk_size: int | None = None,
) -> Tuple[List[List[float]], int]:
    """
    Generate embeddings for large datasets using chunked processing.

    Splits texts into chunks and processes them sequentially to avoid
    overloading Ollama and prevent memory issues.

    Args:
        texts (List[str]): List of text strings to embed
        settings (Settings): Settings instance with embedding config
        chunk_size (int | None): Number of texts per chunk (defaults to config setting)

    Returns:
        Tuple[List[List[float]], int]: List of embedding vectors and their dimension
    """
    if not texts:
        return [], 0

    chunk_size = chunk_size or settings.embedding_chunk_size

    all_embeddings: List[List[float]] = []
    dimension = 0

    for i in range(0, len(texts), chunk_size):
        chunk = texts[i : i + chunk_size]

        try:
            response: EmbedResponse = ollama.embed(
                model=settings.embedding_model,
                input=chunk,
            )

            chunk_embeddings = response.embeddings
            all_embeddings.extend(chunk_embeddings)

            if dimension == 0 and chunk_embeddings:
                dimension = len(chunk_embeddings[0])

            if i + chunk_size < len(texts):
                await asyncio.sleep(0.1)

        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=(
                    f"Error generating embeddings at chunk {i//chunk_size}: {str(exc)}"
                ),
            ) from exc

    return all_embeddings, dimension


def generate_single_embedding(
    text: str,
    settings: Settings,
) -> Tuple[List[float], int]:
    """Generate embedding for a single text using Ollama.

    Args:
        text (str): Text to embed
        settings (Settings): Settings instance with embedding config

    Returns:
        Tuple[List[float], int]: Embedding vector and its dimension
    """
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Text to embed cannot be empty")

    try:
        response: EmbedResponse = ollama.embed(
            model=settings.embedding_model,
            input=text,
        )

        embedding = response.embeddings[0] if response.embeddings else []
        dimension = len(embedding)

        return embedding, dimension

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating embedding with Ollama: {str(exc)}",
        ) from exc
