"""
LLM service for embedding generation using Ollama.
"""

import csv
import io
from typing import List, Tuple
from fastapi import HTTPException
import ollama
from ollama import EmbedResponse
from ..config import settings


def parse_dataset_file(
    content: str, filename: str
) -> Tuple[List[List[str]], List[str], bool, int]:
    """Parse CSV or .data file into records.

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

    # Detect if file has header
    # Strategy: If first row has all non-numeric values and subsequent rows have numeric values, likely header
    has_header = False
    file_ext = filename.split(".")[-1].lower()

    if file_ext == "csv" and len(all_rows) > 1:
        first_row = all_rows[0]
        second_row = all_rows[1] if len(all_rows) > 1 else []

        # Check if first row looks like headers (non-numeric strings)
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

        # If first row is mostly non-numeric and second row is mostly numeric, it's likely a header
        if (
            first_row_numeric < len(first_row) * 0.3
            and second_row_numeric > len(second_row) * 0.5
        ):
            has_header = True

    # Extract column names and data rows
    column_names = []
    data_rows = []
    empty_rows_skipped = 0

    start_idx = 1 if has_header else 0

    if has_header:
        column_names = [str(val).strip() for val in all_rows[0]]

    # Process data rows
    for row in all_rows[start_idx:]:
        # Skip empty rows
        if not row or all(not str(val).strip() for val in row):
            empty_rows_skipped += 1
            continue
        data_rows.append([str(val).strip() for val in row])

    if not data_rows:
        raise HTTPException(status_code=400, detail="No valid data rows found in file")

    # If no header detected, generate column names based on first row length
    if not column_names:
        num_cols = len(data_rows[0]) if data_rows else 0
        column_names = [f"feature_{i}" for i in range(num_cols)]

    return data_rows, column_names, has_header, empty_rows_skipped


def record_to_text(
    record: List[str], column_names: List[str] = None, has_header: bool = False
) -> str:
    """Convert a dataset record to deterministic structured text.

    Uses a stable template format to ensure consistent text representation
    of tabular data for embedding generation.

    Args:
        record (List[str]): List of values in the record
        column_names (List[str] | None): Optional list of column names. If None, uses index-based naming.
        has_header (bool): Whether the dataset has a header row

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


def generate_embeddings_batch(texts: List[str]) -> tuple[List[List[float]], int]:
    """Generate embeddings for a batch of texts using Ollama.

    Args:
        texts (List[str]): List of text strings to embed

    Returns:
        Tuple[List[List[float]], int]: List of embedding vectors and their dimension
    """
    if not texts:
        return [], 0

    try:
        response: EmbedResponse = ollama.embed(
            model=settings.embedding_model,
            input=texts,
        )

        embeddings = response.embeddings

        dimension = len(embeddings[0]) if embeddings else 0

        return embeddings, dimension

    except Exception as e:
        raise Exception(f"Error generating embeddings with Ollama: {str(e)}")


def create_single_embedding(text: str) -> List[List[float]]:
    """Generate embedding for a single text.

    Args:
        text (str): Text to embed

    Returns:
        List[List[float]]: Embedding vector
    """

    # TODO: Implement actual embedding logic using Ollama in future PR.

    single: EmbedResponse = ollama.embed(
        model="nomic-embed-text",
        input=text,
    )

    return single["embeddings"]


def rewrite_query(query: str) -> str:
    """Rewrite a query using context.

    Args:
        query (str): Original query

    Returns:
        str: Rewritten query
    """

    # TODO: Implement actual query rewriting logic using Ollama in future PR.

    return query
