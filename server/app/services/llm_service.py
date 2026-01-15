"""
LLM service for embedding generation using Ollama.
"""

from typing import List
import ollama
from ollama import EmbedResponse


def create_batch_embeddings(args: List[str]) -> List[float]:
    """Generate embeddings for a batch of texts.

    Args:
        args (List[str]): List of texts to embed

    Returns:
        List[float]: List of embedding vectors
    """

    # TODO: Implement actual batch embedding logic using Ollama in future PR.

    batch: EmbedResponse = ollama.embed(
        model="nomic-embed-text",
        input=args,
    )

    return batch["embeddings"]


def create_single_embedding(text: str) -> List[float]:
    """Generate embedding for a single text.

    Args:
        text (str): Text to embed

    Returns:
        List[float]: Embedding vector
    """

    # TODO: Implement actual embedding logic using Ollama in future PR.

    single: EmbedResponse = ollama.embed(
        model="nomic-embed-text",
        input=text,
    )

    return single["embeddings"]


def rewrite_query(query: str, context: str | None = None) -> str:
    """Rewrite a query using context.

    Args:
        query (str): Original query
        context (str | None): Optional context for rewriting

    Returns:
        str: Rewritten query
    """

    # TODO: Implement actual query rewriting logic using Ollama in future PR.

    return None
