"""Create dataset_keys table.

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-15 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    bind = op.get_bind()
    inspector = sa.inspect(bind)

    has_dataset_keys = inspector.has_table("dataset_keys")
    has_legacy_datasetkey = inspector.has_table("datasetkey")

    # If the legacy SQLModel-generated table exists, rename it to preserve data.
    if not has_dataset_keys and has_legacy_datasetkey:
        op.rename_table("datasetkey", "dataset_keys")
        has_dataset_keys = True

    # Fresh installs: create the table if it doesn't exist after rename.
    if not has_dataset_keys:
        op.create_table(
            "dataset_keys",
            sa.Column(
                "id",
                sa.UUID(),
                nullable=False,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("listing_id", sa.Text(), nullable=False),
            sa.Column("key_b64", sa.Text(), nullable=False),
            sa.Column("nonce_b64", sa.Text(), nullable=False),
            sa.Column("dataset_url", sa.Text(), nullable=False),
            sa.Column("dataset_hash", sa.Text(), nullable=False),
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
            sa.PrimaryKeyConstraint("id"),
        )

    # Ensure server-side UUID default for renamed tables.
    op.execute("ALTER TABLE dataset_keys ALTER COLUMN id SET DEFAULT gen_random_uuid()")

    existing_indexes = {
        idx["name"] for idx in inspector.get_indexes("dataset_keys")
    }
    if "ix_dataset_keys_listing_id" not in existing_indexes:
        op.create_index(
            "ix_dataset_keys_listing_id",
            "dataset_keys",
            ["listing_id"],
            unique=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("dataset_keys"):
        existing_indexes = {idx["name"] for idx in inspector.get_indexes("dataset_keys")}
    else:
        existing_indexes = set()

    if "ix_dataset_keys_listing_id" in existing_indexes:
        op.drop_index("ix_dataset_keys_listing_id", table_name="dataset_keys")

    if inspector.has_table("dataset_keys"):
        # Preserve data on downgrade by restoring legacy table name when possible.
        if not inspector.has_table("datasetkey"):
            op.rename_table("dataset_keys", "datasetkey")
        else:
            op.drop_table("dataset_keys")
