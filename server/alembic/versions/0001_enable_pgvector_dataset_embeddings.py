"""Enable pgvector extension and create dataset_embeddings table.

Revision ID: 0001
Revises:
Create Date: 2026-04-13 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable the pgvector extension (idempotent).
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "dataset_embeddings",
        sa.Column("listing_id", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(768), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("listing_id"),
    )

    # HNSW index for fast approximate nearest-neighbour cosine search.
    op.create_index(
        "dataset_embeddings_embedding_hnsw",
        "dataset_embeddings",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_table("dataset_embeddings")
    op.execute("DROP EXTENSION IF EXISTS vector")
