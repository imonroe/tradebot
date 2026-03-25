"""add price_bars table

Revision ID: a3f8c1d2e4b6
Revises: e61bf2a69b1d
Create Date: 2026-03-25 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a3f8c1d2e4b6"
down_revision: Union[str, None] = "e61bf2a69b1d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "price_bars",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("open", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("high", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("low", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("close", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("volume", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", "timestamp", name="uq_price_bar_symbol_ts"),
    )


def downgrade() -> None:
    op.drop_table("price_bars")
