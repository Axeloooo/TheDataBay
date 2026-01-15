"""
LLM router for query rewriting and embedding generation using Ollama.
"""

from fastapi import APIRouter, File, UploadFile, HTTPException
from ..schemas.llm_schema import (
    DatasetEmbeddingResponse,
    VectorSpec,
    DatasetStats,
    QueryRewriteRequest,
    QueryRewriteResponse,
    QueryEmbeddingRequest,
    QueryEmbeddingResponse,
)
from ..services.llm_service import (
    parse_dataset_file,
    record_to_text,
    generate_embeddings_batch,
    generate_single_embedding,
    rewrite_query_with_thinking,
)
from ..config import settings
import csv

router = APIRouter(
    prefix="/llm",
    tags=["llm"],
)


@router.post("/embed/batch", response_model=DatasetEmbeddingResponse)
async def create_batch_embeddings(file: UploadFile = File(...)):
    """Generate embeddings for dataset file (.csv or .data).
    Accepts uploaded dataset file, parses into records,
    transforms each record into deterministic structured text, and
    generates embeddings using Ollama.

    Args:
        file (UploadFile): Dataset file (.csv or .data format)

    Returns:
        DatasetEmbeddingResponse: Complete embedding response with signature, vectorSpec, and stats

    Raises:
        HTTPException: If file format is not supported or file is invalid
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    file_extension = file.filename.split(".")[-1].lower()

    if file_extension not in ["csv", "data"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: .{file_extension}. Only .csv and .data files are supported.",
        )

    try:
        content = await file.read()
        decoded_content = content.decode("utf-8")

        data_rows, column_names, has_header, empty_rows_skipped = parse_dataset_file(
            decoded_content, file.filename
        )

        texts = []
        for row in data_rows:
            text = record_to_text(row, column_names)
            texts.append(text)

        embeddings, dimension = generate_embeddings_batch(texts)

        total_columns = len(column_names)
        total_rows = len(data_rows)

        vector_spec = VectorSpec(
            model=settings.embedding_model,
            dimension=dimension,
        )

        stats = DatasetStats(
            total_rows=total_rows,
            total_columns=total_columns,
            empty_rows_skipped=empty_rows_skipped,
            has_header=has_header,
        )

        return DatasetEmbeddingResponse(
            signature=embeddings,
            vectorSpec=vector_spec,
            stats=stats,
            filename=file.filename,
        )

    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="File encoding error. Please ensure file is UTF-8 encoded.",
        )

    except csv.Error as e:
        raise HTTPException(status_code=400, detail=f"CSV parsing error: {str(e)}")

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@router.post("/rewrite", response_model=QueryRewriteResponse)
async def rewrite_query(request: QueryRewriteRequest):
    """Rewrite query using a 'thinking' model.

    Takes a natural language query and rewrites it to be more explicit
    and retrieval-friendly using the configured thinking model.

    Args:
        request (QueryRewriteRequest): Query rewrite request model

    Returns:
        QueryRewriteResponse: Query rewrite response model
    """
    rewritten = rewrite_query_with_thinking(request.query, request.context)

    return QueryRewriteResponse(
        original_query=request.query,
        rewritten_query=rewritten,
        model=settings.thinking_model,
    )


@router.post("/embed/query", response_model=QueryEmbeddingResponse)
async def embed_query(request: QueryEmbeddingRequest):
    """Rewrite and embed a query for retrieval.

    This endpoint performs the complete query processing pipeline:
    1. Rewrites the query using the thinking model for better retrieval
    2. Embeds the rewritten query using the embedding model
    3. Returns vectorSpec compatible with dataset embeddings

    Args:
        request (QueryEmbeddingRequest): Query embedding request

    Returns:
        QueryEmbeddingResponse: Complete response with rewritten query, embedding, and vectorSpec
    """
    # rewritten_query = rewrite_query_with_thinking(request.query, request.context)

    query_embedding, dimension = generate_single_embedding(request.query)

    vector_spec = VectorSpec(
        model=settings.embedding_model,
        dimension=dimension,
    )

    return QueryEmbeddingResponse(
        original_query=request.query,
        rewritten_query=request.query,
        query_embedding=query_embedding,
        vectorSpec=vector_spec,
        rewrite_model=settings.thinking_model,
    )
