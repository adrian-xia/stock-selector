"""add optimization_tasks and optimization_results tables

Revision ID: a1f3c8d92e47
Revises: 4b493b32b694
Create Date: 2026-02-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "a1f3c8d92e47"
down_revision = "4b493b32b694"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "optimization_tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("strategy_name", sa.String(64), nullable=False),
        sa.Column("algorithm", sa.String(16), nullable=False),
        sa.Column("param_space", postgresql.JSONB(), nullable=False),
        sa.Column("stock_codes", postgresql.JSONB(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("initial_capital", sa.Numeric(20, 2), server_default="1000000"),
        sa.Column("ga_config", postgresql.JSONB(), nullable=True),
        sa.Column("top_n", sa.Integer(), server_default="20"),
        sa.Column("status", sa.String(16), server_default="pending"),
        sa.Column("progress", sa.Integer(), server_default="0"),
        sa.Column("total_combinations", sa.Integer(), nullable=True),
        sa.Column("completed_combinations", sa.Integer(), server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "optimization_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("params", postgresql.JSONB(), nullable=False),
        sa.Column("sharpe_ratio", sa.Numeric(10, 4), nullable=True),
        sa.Column("annual_return", sa.Numeric(10, 4), nullable=True),
        sa.Column("max_drawdown", sa.Numeric(10, 4), nullable=True),
        sa.Column("win_rate", sa.Numeric(10, 4), nullable=True),
        sa.Column("total_trades", sa.Integer(), nullable=True),
        sa.Column("total_return", sa.Numeric(10, 4), nullable=True),
        sa.Column("volatility", sa.Numeric(10, 4), nullable=True),
        sa.Column("calmar_ratio", sa.Numeric(10, 4), nullable=True),
        sa.Column("sortino_ratio", sa.Numeric(10, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_optimization_results_task_id", "optimization_results", ["task_id"])


def downgrade() -> None:
    op.drop_index("ix_optimization_results_task_id", table_name="optimization_results")
    op.drop_table("optimization_results")
    op.drop_table("optimization_tasks")
