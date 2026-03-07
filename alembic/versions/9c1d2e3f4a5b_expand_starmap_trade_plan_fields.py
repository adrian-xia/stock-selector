"""expand trade_plan_daily_ext for unified execution plans

Revision ID: 9c1d2e3f4a5b
Revises: 8b2c7d1a4e9f
Create Date: 2026-03-07 20:40:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9c1d2e3f4a5b"
down_revision: Union[str, Sequence[str], None] = "8b2c7d1a4e9f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("trade_plan_daily_ext", sa.Column("valid_date", sa.Date(), nullable=True))
    op.add_column(
        "trade_plan_daily_ext",
        sa.Column("direction", sa.String(length=16), nullable=False, server_default="buy"),
    )
    op.add_column("trade_plan_daily_ext", sa.Column("trigger_price", sa.Numeric(20, 4), nullable=True))
    op.add_column("trade_plan_daily_ext", sa.Column("stop_loss_price", sa.Numeric(20, 4), nullable=True))
    op.add_column("trade_plan_daily_ext", sa.Column("take_profit_price", sa.Numeric(20, 4), nullable=True))
    op.add_column("trade_plan_daily_ext", sa.Column("risk_reward_ratio", sa.Numeric(10, 4), nullable=True))
    op.add_column("trade_plan_daily_ext", sa.Column("triggered", sa.Boolean(), nullable=True))
    op.add_column("trade_plan_daily_ext", sa.Column("actual_price", sa.Numeric(20, 4), nullable=True))


def downgrade() -> None:
    op.drop_column("trade_plan_daily_ext", "actual_price")
    op.drop_column("trade_plan_daily_ext", "triggered")
    op.drop_column("trade_plan_daily_ext", "risk_reward_ratio")
    op.drop_column("trade_plan_daily_ext", "take_profit_price")
    op.drop_column("trade_plan_daily_ext", "stop_loss_price")
    op.drop_column("trade_plan_daily_ext", "trigger_price")
    op.drop_column("trade_plan_daily_ext", "direction")
    op.drop_column("trade_plan_daily_ext", "valid_date")
