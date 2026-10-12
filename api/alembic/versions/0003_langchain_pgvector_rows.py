"""Replace mean-pooled listing embeddings with LangChain row vectors.

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-26 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    if not inspector.has_table(table_name):
        return False
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("langchain_pg_collection"):
        op.create_table(
            "langchain_pg_collection",
            sa.Column(
                "uuid",
                sa.UUID(),
                nullable=False,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("name", sa.String(), nullable=True),
            sa.Column("cmetadata", sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint("uuid"),
            sa.UniqueConstraint("name", name="uq_langchain_pg_collection_name"),
        )

    if not inspector.has_table("langchain_pg_embedding"):
        op.create_table(
            "langchain_pg_embedding",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("collection_id", sa.UUID(), nullable=True),
            sa.Column("embedding", Vector(768), nullable=True),
            sa.Column("document", sa.String(), nullable=True),
            sa.Column("cmetadata", postgresql.JSONB(), nullable=True),
            sa.ForeignKeyConstraint(
                ["collection_id"],
                ["langchain_pg_collection.uuid"],
                name="langchain_pg_embedding_collection_id_fkey",
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
        )

    embedding_indexes = {
        idx["name"] for idx in inspector.get_indexes("langchain_pg_embedding")
    }
    if "ix_langchain_pg_embedding_collection_id" not in embedding_indexes:
        op.create_index(
            "ix_langchain_pg_embedding_collection_id",
            "langchain_pg_embedding",
            ["collection_id"],
        )
    if "ix_langchain_pg_embedding_cmetadata_gin" not in embedding_indexes:
        op.create_index(
            "ix_langchain_pg_embedding_cmetadata_gin",
            "langchain_pg_embedding",
            ["cmetadata"],
            postgresql_using="gin",
            postgresql_ops={"cmetadata": "jsonb_path_ops"},
        )
    if "ix_langchain_pg_embedding_listing_id" not in embedding_indexes:
        op.create_index(
            "ix_langchain_pg_embedding_listing_id",
            "langchain_pg_embedding",
            [sa.text("(cmetadata->>'listing_id')")],
        )
    if "langchain_pg_embedding_embedding_hnsw" not in embedding_indexes:
        op.create_index(
            "langchain_pg_embedding_embedding_hnsw",
            "langchain_pg_embedding",
            ["embedding"],
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        )

    if inspector.has_table("dataset_embeddings"):
        op.drop_table("dataset_embeddings")

    for column_name in ("signature_url", "signature_hash"):
        if _has_column(inspector, "dataset_keys", column_name):
            op.drop_column("dataset_keys", column_name)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for column_name, column_type in (
        ("signature_url", sa.Text()),
        ("signature_hash", sa.Text()),
    ):
        if not _has_column(inspector, "dataset_keys", column_name):
            op.add_column(
                "dataset_keys",
                sa.Column(column_name, column_type, nullable=True),
            )

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
    op.create_index(
        "dataset_embeddings_embedding_hnsw",
        "dataset_embeddings",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    op.drop_index(
        "langchain_pg_embedding_embedding_hnsw",
        table_name="langchain_pg_embedding",
    )
    op.drop_index(
        "ix_langchain_pg_embedding_listing_id",
        table_name="langchain_pg_embedding",
    )
    op.drop_index(
        "ix_langchain_pg_embedding_cmetadata_gin",
        table_name="langchain_pg_embedding",
    )
    op.drop_index(
        "ix_langchain_pg_embedding_collection_id",
        table_name="langchain_pg_embedding",
    )
    op.drop_table("langchain_pg_embedding")
    op.drop_table("langchain_pg_collection")
