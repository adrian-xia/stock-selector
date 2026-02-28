"""V4: 新增 strategy_watchpool + v4_backtest_results 表

Revision ID: g1a2b3c4d5e6
Revises: f3a4b5c6d7e8
Create Date: 2026-02-28
"""
from alembic import op
import sqlalchemy as sa

revision = "g1a2b3c4d5e6"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "strategy_watchpool",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ts_code", sa.String(16), nullable=False),
        sa.Column("strategy_name", sa.String(64), nullable=False, server_default="volume-price-pattern"),
        sa.Column("t0_date", sa.Date, nullable=False),
        sa.Column("t0_close", sa.Numeric(20, 4)),
        sa.Column("t0_open", sa.Numeric(20, 4)),
        sa.Column("t0_low", sa.Numeric(20, 4)),
        sa.Column("t0_volume", sa.BigInteger),
        sa.Column("t0_pct_chg", sa.Numeric(10, 4)),
        sa.Column("status", sa.String(16), nullable=False, server_default="watching"),
        sa.Column("washout_days", sa.Integer, server_default="0"),
        sa.Column("min_washout_vol", sa.BigInteger),
        sa.Column("min_washout_low", sa.Numeric(20, 4)),
        sa.Column("sector_score", sa.Numeric(10, 4)),
        sa.Column("market_score", sa.Numeric(10, 4)),
        sa.Column("triggered_date", sa.Date),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("ts_code", "t0_date", "strategy_name", name="uq_watchpool_code_date_strategy"),
    )
    op.create_index("idx_watchpool_status", "strategy_watchpool", ["status"])
    op.create_index("idx_watchpool_date", "strategy_watchpool", ["t0_date"])

    op.create_table(
        "v4_backtest_results",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("strategy_name", sa.String(64), nullable=False, server_default="volume-price-pattern"),
        sa.Column("params", sa.JSON, nullable=False),
        sa.Column("backtest_start", sa.Date, nullable=False),
        sa.Column("backtest_end", sa.Date, nullable=False),
        sa.Column("total_signals", sa.Integer),
        sa.Column("signals_per_month", sa.Numeric(8, 2)),
        sa.Column("win_rate_1d", sa.Numeric(6, 4)),
        sa.Column("win_rate_3d", sa.Numeric(6, 4)),
        sa.Column("win_rate_5d", sa.Numeric(6, 4)),
        sa.Column("win_rate_10d", sa.Numeric(6, 4)),
        sa.Column("avg_ret_5d", sa.Numeric(8, 4)),
        sa.Column("profit_loss_ratio", sa.Numeric(8, 4)),
        sa.Column("max_drawdown", sa.Numeric(8, 4)),
        sa.Column("sharpe_ratio", sa.Numeric(8, 4)),
        sa.Column("composite_score", sa.Numeric(8, 4)),
        sa.Column("signals", sa.JSON),
        sa.Column("is_grid_search", sa.Boolean, server_default="false"),
        sa.Column("grid_search_id", sa.String(36)),
        sa.Column("rank_in_grid", sa.Integer),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_v4bt_run_id", "v4_backtest_results", ["run_id"])
    op.create_index("idx_v4bt_grid_id", "v4_backtest_results", ["grid_search_id"])
    op.create_index("idx_v4bt_score", "v4_backtest_results", ["composite_score"])


def downgrade() -> None:
    op.drop_table("v4_backtest_results")
    op.drop_table("strategy_watchpool")
