"""新增 strategy_picks 和 strategy_hit_stats 表（策略历史命中率追踪）

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-27
"""

from alembic import op
import sqlalchemy as sa

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- strategy_picks ---
    op.create_table(
        "strategy_picks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("strategy_name", sa.String(64), nullable=False),
        sa.Column("pick_date", sa.Date(), nullable=False),
        sa.Column("ts_code", sa.String(16), nullable=False),
        sa.Column("pick_score", sa.Numeric(10, 4), nullable=True),
        sa.Column("pick_close", sa.Numeric(20, 4), nullable=True),
        sa.Column("return_1d", sa.Numeric(10, 4), nullable=True),
        sa.Column("return_3d", sa.Numeric(10, 4), nullable=True),
        sa.Column("return_5d", sa.Numeric(10, 4), nullable=True),
        sa.Column("return_10d", sa.Numeric(10, 4), nullable=True),
        sa.Column("return_20d", sa.Numeric(10, 4), nullable=True),
        sa.Column("max_return", sa.Numeric(10, 4), nullable=True),
        sa.Column("max_drawdown", sa.Numeric(10, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("strategy_name", "pick_date", "ts_code", name="uq_picks_strategy_date_code"),
    )
    op.create_index("idx_picks_strategy_date", "strategy_picks", ["strategy_name", "pick_date"])
    op.create_index("idx_picks_date", "strategy_picks", ["pick_date"])
    op.create_index("idx_picks_code", "strategy_picks", ["ts_code"])

    # --- strategy_hit_stats ---
    op.create_table(
        "strategy_hit_stats",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("strategy_name", sa.String(64), nullable=False),
        sa.Column("stat_date", sa.Date(), nullable=False),
        sa.Column("period", sa.String(8), nullable=False),
        sa.Column("total_picks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("win_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("hit_rate", sa.Numeric(10, 4), nullable=True),
        sa.Column("avg_return", sa.Numeric(10, 4), nullable=True),
        sa.Column("median_return", sa.Numeric(10, 4), nullable=True),
        sa.Column("best_return", sa.Numeric(10, 4), nullable=True),
        sa.Column("worst_return", sa.Numeric(10, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("strategy_name", "stat_date", "period", name="uq_hit_stats_strategy_date_period"),
    )
    op.create_index("idx_hit_stats_strategy", "strategy_hit_stats", ["strategy_name"])


def downgrade() -> None:
    op.drop_index("idx_hit_stats_strategy", table_name="strategy_hit_stats")
    op.drop_table("strategy_hit_stats")

    op.drop_index("idx_picks_code", table_name="strategy_picks")
    op.drop_index("idx_picks_date", table_name="strategy_picks")
    op.drop_index("idx_picks_strategy_date", table_name="strategy_picks")
    op.drop_table("strategy_picks")
