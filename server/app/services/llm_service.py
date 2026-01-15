"""
LLM service for embedding generation using Ollama.
"""

import csv
import io
from typing import List, Tuple
from fastapi import HTTPException
import ollama
from ollama import ChatResponse, EmbedResponse
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
    record: List[str],
    column_names: List[str] = None,
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
        raise HTTPException(
            status_code=500,
            detail=f"Error generating embeddings with Ollama: {str(e)}",
        )


def generate_single_embedding(text: str) -> Tuple[List[float], int]:
    """Generate embedding for a single text using Ollama.

    Args:
        text (str): Text to embed

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

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating embedding with Ollama: {str(e)}",
        )


def rewrite_query_with_thinking(query: str, context: str = None) -> str:
    """Rewrite a query using a thinking model to make it more retrieval-friendly.

    Args:
        query (str): Original user query
        context (str): Optional context to inform rewriting

    Returns:
        str: Rewritten query optimized for retrieval
    """
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        system_prompt = """
        You rewrite user queries into a single, explicit, retrieval-friendly query for semantic search over structured medical tabular records.
        Rules:
        - Preserve the user's intent; do not add new constraints or numeric thresholds that were not stated.
        - Expand abbreviations and normalize phrasing to match dataset field concepts (e.g., age, sex, cholesterol, resting blood pressure, chest pain, exercise-induced angina, maximum heart rate, ST depression, ECG).
        - If the user gives ranges (e.g., 50-65), keep them. If they say "high" or "low", keep it qualitative (do not guess a number).
        - Keep the output concise: one sentence or a short phrase.
        - Output ONLY the rewritten query text. No labels, no bullets, no explanations.
        """.strip()

        user_message: str = f"Query: {query}"

        if context:
            user_message += f"\nContext: {context}"

        response: ChatResponse = ollama.chat(
            model=settings.thinking_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )

        rewritten_query: str | None = response.message.content

        if not rewritten_query:
            return query

        return rewritten_query

    except Exception as e:
        print(f"Query rewriting failed: {str(e)}")
        return query
