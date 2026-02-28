"""add market_optimization_tasks table

Revision ID: h2b3c4d5e6f7
Revises: g1a2b3c4d5e6
Create Date: 2026-02-28
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "h2b3c4d5e6f7"
down_revision = "g1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_optimization_tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("strategy_name", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("param_space", postgresql.JSONB(), nullable=True),
        sa.Column("lookback_days", sa.Integer(), server_default="120"),
        sa.Column("total_combinations", sa.Integer(), nullable=True),
        sa.Column("completed_combinations", sa.Integer(), server_default="0"),
        sa.Column("progress", sa.Integer(), server_default="0"),
        sa.Column("best_params", postgresql.JSONB(), nullable=True),
        sa.Column("best_score", sa.Numeric(10, 6), nullable=True),
        sa.Column("result_detail", postgresql.JSONB(), nullable=True),
        sa.Column("auto_apply", sa.Boolean(), server_default="true"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_mopt_strategy", "market_optimization_tasks", ["strategy_name"])
    op.create_index("idx_mopt_status", "market_optimization_tasks", ["status"])


def downgrade() -> None:
    op.drop_index("idx_mopt_status", table_name="market_optimization_tasks")
    op.drop_index("idx_mopt_strategy", table_name="market_optimization_tasks")
    op.drop_table("market_optimization_tasks")
