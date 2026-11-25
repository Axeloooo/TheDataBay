"""Record the uploading seller on each dataset key.

Key release now requires the on-chain listing's seller to match the wallet
that uploaded the dataset, so a listing ID claimed by someone else cannot be
used to obtain the key. Existing rows stay NULL and keep the old behaviour.

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-25 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return column in {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    if not _has_column("dataset_keys", "seller_address"):
        op.add_column(
            "dataset_keys", sa.Column("seller_address", sa.Text(), nullable=True)
        )


def downgrade() -> None:
    if _has_column("dataset_keys", "seller_address"):
        op.drop_column("dataset_keys", "seller_address")
