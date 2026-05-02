"""PGVector repository for dataset summary embeddings."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langchain_core.documents import Document
from langchain_postgres import PGVector
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

DATASET_SUMMARIES_COLLECTION = "dataset_summaries"


class PGVectorRepository:
    """Data-access boundary for LangChain PGVector dataset summaries."""

    def __init__(
        self,
        *,
        connection: str,
        embeddings: Any,
        embedding_dimension: int,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        collection_name: str = DATASET_SUMMARIES_COLLECTION,
        pgvector_cls: type[PGVector] | None = None,
    ) -> None:
        self._connection = connection
        self._embeddings = embeddings
        self._embedding_dimension = embedding_dimension
        self._session_factory = session_factory
        self._collection_name = collection_name
        self._pgvector_cls = pgvector_cls or PGVector
        self._vectorstore: Any | None = None

    async def create_collection(self) -> None:
        """Create the configured PGVector collection if needed."""
        await self._get_vectorstore().acreate_collection()

    async def add_documents(self, docs: Sequence[Document], ids: list[str]) -> None:
        """Persist dataset summary documents with stable caller-provided IDs."""
        await self._get_vectorstore().aadd_documents(docs, ids=ids)

    async def similarity_search_by_vector(
        self,
        vector: list[float],
        k: int,
    ) -> list[tuple[Document, float]]:
        """Return summary hits with cosine similarity scores."""
        hits = await self._get_vectorstore().asimilarity_search_with_score_by_vector(
            vector,
            k=k,
        )
        return [
            (document, _distance_to_similarity(float(distance)))
            for document, distance in hits
        ]

    async def delete_stale_documents(
        self,
        listing_id: str,
        current_ids: list[str],
    ) -> None:
        """Delete summary documents for a listing that are no longer current."""
        if self._session_factory is None:
            raise RuntimeError("session_factory is required to delete stale documents")

        async with self._session_factory() as session:
            async with session.begin():
                await session.execute(
                    text(
                        """
                        DELETE FROM langchain_pg_embedding e
                        USING langchain_pg_collection c
                        WHERE e.collection_id = c.uuid
                          AND c.name = :collection_name
                          AND e.cmetadata->>'listing_id' = :listing_id
                          AND e.id != ALL(:current_ids)
                        """
                    ),
                    {
                        "collection_name": self._collection_name,
                        "listing_id": listing_id,
                        "current_ids": current_ids,
                    },
                )

    def _get_vectorstore(self) -> Any:
        if self._vectorstore is None:
            self._vectorstore = self._pgvector_cls(
                embeddings=self._embeddings,
                collection_name=self._collection_name,
                connection=self._connection,
                embedding_length=self._embedding_dimension,
                use_jsonb=True,
                create_extension=True,
                async_mode=True,
            )
        return self._vectorstore


def _distance_to_similarity(distance: float) -> float:
    """Convert LangChain PGVector cosine distance to a similarity score."""
    return round(1.0 - distance, 12)


def pgvector_repository_for_settings(
    settings: Any,
    *,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
    pgvector_cls: type[PGVector] | None = None,
    embeddings: Any | None = None,
) -> PGVectorRepository:
    """Build a PGVector repository from application settings."""
    if embeddings is None:
        raise RuntimeError("embeddings must be provided by the llm domain")
    return PGVectorRepository(
        connection=settings.psycopg_database_url,
        embeddings=embeddings,
        embedding_dimension=settings.llm_embedding_dimension,
        session_factory=session_factory,
        pgvector_cls=pgvector_cls,
    )
