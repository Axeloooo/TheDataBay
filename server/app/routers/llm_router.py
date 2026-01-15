"""
LLM router for query rewriting and embedding generation using Ollama.
"""

from fastapi import APIRouter, File, UploadFile, HTTPException
from ..schemas.llm import (
    EmbeddingRequest,
    EmbeddingResponse,
    BatchEmbeddingFileResponse,
    QueryRewriteRequest,
    QueryRewriteResponse,
)
from ..config import settings
import csv
import io

router = APIRouter(
    prefix="/llm",
    tags=["llm"],
)


@router.post("/embed", response_model=EmbeddingResponse)
async def create_embedding(request: EmbeddingRequest):
    """Generate embedding for a single text.

    Args:
        request (EmbeddingRequest): Embedding request model

    Returns:
        EmbeddingResponse: Embedding response model
    """

    # TODO: Implement actual embedding logic in future PR.

    # Placeholder implementation
    return EmbeddingResponse(embedding=[0.0] * 768, model=settings.embedding_model)


@router.post("/embed/batch", response_model=BatchEmbeddingFileResponse)
async def create_batch_embeddings(file: UploadFile = File(...)):
    """Generate embeddings for dataset file (.csv or .data).

    Args:
        file (UploadFile): Dataset file (.csv or .data format)

    Returns:
        BatchEmbeddingFileResponse: Batch embedding response with file metadata

    Raises:
        HTTPException: If file format is not supported or file is invalid
    """
    # Validate file extension
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    file_extension = file.filename.split(".")[-1].lower()
    if file_extension not in ["csv", "data"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: .{file_extension}. Only .csv and .data files are supported.",
        )

    try:
        # Read file content
        content = await file.read()
        decoded_content = content.decode("utf-8")

        # Parse CSV/data file
        csv_reader = csv.reader(io.StringIO(decoded_content))
        rows = list(csv_reader)

        if not rows:
            raise HTTPException(status_code=400, detail="File is empty")

        # TODO: Implement actual batch embedding logic in future PR.

        # For now, return placeholder embeddings
        embeddings = [[0.0] * 768 for _ in rows[:100]]

        return BatchEmbeddingFileResponse(
            embeddings=embeddings,
            model=settings.embedding_model,
            count=len(rows),
            filename=file.filename,
            rows_processed=len(rows),
        )

    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="File encoding error. Please ensure file is UTF-8 encoded.",
        )
    except csv.Error as e:
        raise HTTPException(status_code=400, detail=f"CSV parsing error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@router.post("/rewrite", response_model=QueryRewriteResponse)
async def rewrite_query(request: QueryRewriteRequest):
    """Rewrite query using a 'thinking' model.

    Args:
        request (QueryRewriteRequest): Query rewrite request model

    Returns:
        QueryRewriteResponse: Query rewrite response model
    """

    # TODO: Implement actual query rewriting logic in future PR.

    # Placeholder implementation
    return QueryRewriteResponse(
        original_query=request.query,
        rewritten_query=request.query,
        model=settings.thinking_model,
    )
