"""
LLM service for embedding generation using Ollama.
"""

from typing import List
import ollama
from ollama import EmbedResponse


def create_batch_embeddings(data: List[List[any]]) -> List[List[float]]:
    """Generate embeddings for a batch of texts.

    Args:
        data (List[List[any]]): List of lists of data to embed
    Returns:
        List[List[float]]: List of embedding vectors
    """

    # TODO: Implement actual batch embedding logic using Ollama in future PR.

    batch: EmbedResponse = ollama.embed(
        model="nomic-embed-text",
        input=data,
    )

    return batch["embeddings"]


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
