"""Create durable dataset preview metadata table.

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-28 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("dataset_previews"):
        op.create_table(
            "dataset_previews",
            sa.Column(
                "id",
                sa.UUID(),
                nullable=False,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("listing_id", sa.Text(), nullable=False),
            sa.Column("preview", sa.JSON(), nullable=False),
            sa.Column("stats", sa.JSON(), nullable=True),
            sa.Column("vector_spec", sa.JSON(), nullable=True),
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

    existing_indexes = {
        idx["name"] for idx in inspector.get_indexes("dataset_previews")
    }
    if "ix_dataset_previews_listing_id" not in existing_indexes:
        op.create_index(
            "ix_dataset_previews_listing_id",
            "dataset_previews",
            ["listing_id"],
            unique=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("dataset_previews"):
        existing_indexes = {
            idx["name"] for idx in inspector.get_indexes("dataset_previews")
        }
        if "ix_dataset_previews_listing_id" in existing_indexes:
            op.drop_index(
                "ix_dataset_previews_listing_id",
                table_name="dataset_previews",
            )
        op.drop_table("dataset_previews")
