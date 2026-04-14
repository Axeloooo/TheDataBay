"""
Repository for DatasetEmbedding — pgvector upsert, cosine similarity search,
and delete operations.

All write methods flush but do NOT commit; the caller owns the transaction.
"""

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.dataset_embedding import DatasetEmbedding
from .base import BaseRepository


class DatasetEmbeddingRepository(BaseRepository[DatasetEmbedding]):
    """Async repository for dataset embedding vectors."""

    def __init__(self) -> None:
        super().__init__(DatasetEmbedding)

    async def upsert(
        self,
        db: AsyncSession,
        listing_id: str,
        embedding: list[float],
    ) -> DatasetEmbedding:
        """Insert or update the embedding for a listing.

        On conflict on listing_id, updates the embedding and bumps updated_at
        to the current time.  Flushes but does NOT commit.

        Args:
            db: Open async database session.
            listing_id: On-chain marketplace listing identifier.
            embedding: 768-dimensional float vector.

        Returns:
            The upserted DatasetEmbedding row.
        """
        stmt = (
            pg_insert(DatasetEmbedding)
            .values(listing_id=listing_id, embedding=embedding)
            .on_conflict_do_update(
                index_elements=["listing_id"],
                set_={
                    "embedding": embedding,
                    "updated_at": text("now()"),
                },
            )
            .returning(DatasetEmbedding)
        )
        result = await db.execute(stmt)
        row = result.scalar_one()
        await db.flush()
        return row

    async def search_by_vector(
        self,
        db: AsyncSession,
        query_vec: list[float],
        limit: int = 20,
    ) -> list[tuple[str, float]]:
        """Find the closest embeddings using cosine similarity.

        Cosine similarity score = 1 - (cosine distance).  Higher is more
        similar.  Results are ordered from most to least similar.

        Args:
            db: Open async database session.
            query_vec: 768-dimensional query vector.
            limit: Maximum number of results to return (default 20).

        Returns:
            List of (listing_id, similarity_score) tuples ordered by score
            descending (most similar first).
        """
        stmt = text(
            """
            SELECT listing_id,
                   1 - (embedding <=> CAST(:q AS vector(768))) AS score
            FROM dataset_embeddings
            ORDER BY embedding <=> CAST(:q AS vector(768)) ASC
            LIMIT :limit
            """
        )
        result = await db.execute(
            stmt,
            {"q": str(query_vec), "limit": limit},
        )
        return [(row[0], float(row[1])) for row in result.fetchall()]

    async def delete(self, db: AsyncSession, id: str) -> None:  # type: ignore[override]
        """Delete the embedding row for a listing.

        Flushes but does NOT commit.

        Args:
            db: Open async database session.
            id: On-chain marketplace listing identifier (listing_id PK).
        """
        stmt = text(
            "DELETE FROM dataset_embeddings WHERE listing_id = :listing_id"
        )
        await db.execute(stmt, {"listing_id": id})
        await db.flush()
