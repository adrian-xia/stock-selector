"""add market_regime_daily table

Revision ID: 8b2c7d1a4e9f
Revises: 293b80375079
Create Date: 2026-03-07 03:40:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8b2c7d1a4e9f"
down_revision: Union[str, Sequence[str], None] = "293b80375079"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "market_regime_daily",
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("benchmark_code", sa.String(length=16), nullable=False, server_default="000001.SH"),
        sa.Column("regime", sa.String(length=16), nullable=False),
        sa.Column("close", sa.Numeric(20, 4), nullable=True),
        sa.Column("ma20", sa.Numeric(20, 4), nullable=True),
        sa.Column("ma60", sa.Numeric(20, 4), nullable=True),
        sa.Column("prev_ma20", sa.Numeric(20, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("trade_date"),
    )
    op.create_index(
        "idx_market_regime_daily_regime",
        "market_regime_daily",
        ["regime"],
    )


def downgrade() -> None:
    op.drop_index("idx_market_regime_daily_regime", table_name="market_regime_daily")
    op.drop_table("market_regime_daily")
