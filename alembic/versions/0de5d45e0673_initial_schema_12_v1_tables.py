"""initial schema - 12 V1 tables

Revision ID: 0de5d45e0673
Revises:
Create Date: 2026-02-07 23:23:52.758940

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0de5d45e0673"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # trade_calendar
    op.create_table(
        "trade_calendar",
        sa.Column("cal_date", sa.Date(), nullable=False),
        sa.Column("exchange", sa.String(10), nullable=False, server_default="SSE"),
        sa.Column("is_open", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("pre_trade_date", sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint("cal_date", "exchange"),
    )

    # stocks
    op.create_table(
        "stocks",
        sa.Column("ts_code", sa.String(16), nullable=False),
        sa.Column("symbol", sa.String(10), nullable=True),
        sa.Column("name", sa.String(32), nullable=False),
        sa.Column("area", sa.String(20), nullable=True),
        sa.Column("industry", sa.String(50), nullable=True),
        sa.Column("market", sa.String(16), nullable=True),
        sa.Column("list_date", sa.Date(), nullable=True),
        sa.Column("list_status", sa.String(4), nullable=False, server_default="L"),
        sa.Column("is_hs", sa.String(4), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("ts_code"),
    )

    # stock_daily
    op.create_table(
        "stock_daily",
        sa.Column("ts_code", sa.String(16), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("open", sa.Numeric(10, 2), nullable=False),
        sa.Column("high", sa.Numeric(10, 2), nullable=False),
        sa.Column("low", sa.Numeric(10, 2), nullable=False),
        sa.Column("close", sa.Numeric(10, 2), nullable=False),
        sa.Column("pre_close", sa.Numeric(10, 2), nullable=True),
        sa.Column("pct_chg", sa.Numeric(10, 4), nullable=True),
        sa.Column("vol", sa.Numeric(20, 2), nullable=False, server_default="0"),
        sa.Column("amount", sa.Numeric(20, 2), nullable=False, server_default="0"),
        sa.Column("adj_factor", sa.Numeric(16, 6), nullable=True),
        sa.Column("turnover_rate", sa.Numeric(10, 4), nullable=True),
        sa.Column("trade_status", sa.String(4), nullable=False, server_default="1"),
        sa.Column("data_source", sa.String(16), nullable=False, server_default="baostock"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("ts_code", "trade_date"),
    )
    op.create_index("idx_stock_daily_code_date", "stock_daily", ["ts_code", sa.text("trade_date DESC")])
    op.create_index("idx_stock_daily_trade_date", "stock_daily", ["trade_date"])

    # stock_min
    op.create_table(
        "stock_min",
        sa.Column("ts_code", sa.String(16), nullable=False),
        sa.Column("trade_time", sa.DateTime(), nullable=False),
        sa.Column("freq", sa.String(8), nullable=False, server_default="5min"),
        sa.Column("open", sa.Numeric(10, 2), nullable=False),
        sa.Column("high", sa.Numeric(10, 2), nullable=False),
        sa.Column("low", sa.Numeric(10, 2), nullable=False),
        sa.Column("close", sa.Numeric(10, 2), nullable=False),
        sa.Column("vol", sa.Numeric(20, 2), nullable=False, server_default="0"),
        sa.Column("amount", sa.Numeric(20, 2), nullable=False, server_default="0"),
        sa.Column("data_source", sa.String(16), nullable=False, server_default="baostock"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("ts_code", "trade_time", "freq"),
    )
    op.create_index("idx_stock_min_code_time", "stock_min", ["ts_code", sa.text("trade_time DESC")])

    # finance_indicator
    op.create_table(
        "finance_indicator",
        sa.Column("ts_code", sa.String(16), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("report_type", sa.String(8), nullable=False, server_default="Q"),
        sa.Column("ann_date", sa.Date(), nullable=True),
        sa.Column("eps", sa.Numeric(10, 4), nullable=True),
        sa.Column("roe", sa.Numeric(10, 4), nullable=True),
        sa.Column("roe_diluted", sa.Numeric(10, 4), nullable=True),
        sa.Column("gross_margin", sa.Numeric(10, 4), nullable=True),
        sa.Column("net_margin", sa.Numeric(10, 4), nullable=True),
        sa.Column("revenue_yoy", sa.Numeric(10, 4), nullable=True),
        sa.Column("profit_yoy", sa.Numeric(10, 4), nullable=True),
        sa.Column("pe_ttm", sa.Numeric(12, 4), nullable=True),
        sa.Column("pb", sa.Numeric(10, 4), nullable=True),
        sa.Column("ps_ttm", sa.Numeric(10, 4), nullable=True),
        sa.Column("total_mv", sa.Numeric(20, 2), nullable=True),
        sa.Column("circ_mv", sa.Numeric(20, 2), nullable=True),
        sa.Column("current_ratio", sa.Numeric(10, 4), nullable=True),
        sa.Column("quick_ratio", sa.Numeric(10, 4), nullable=True),
        sa.Column("debt_ratio", sa.Numeric(10, 4), nullable=True),
        sa.Column("ocf_per_share", sa.Numeric(10, 4), nullable=True),
        sa.Column("data_source", sa.String(16), nullable=False, server_default="baostock"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("ts_code", "end_date", "report_type"),
    )
    op.create_index("idx_finance_code_date", "finance_indicator", ["ts_code", sa.text("end_date DESC")])
    op.create_index("idx_finance_end_date", "finance_indicator", ["end_date"])
    op.create_index("idx_finance_ann_date", "finance_indicator", ["ann_date"])

    # technical_daily
    op.create_table(
        "technical_daily",
        sa.Column("ts_code", sa.String(16), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("ma5", sa.Numeric(10, 2), nullable=True),
        sa.Column("ma10", sa.Numeric(10, 2), nullable=True),
        sa.Column("ma20", sa.Numeric(10, 2), nullable=True),
        sa.Column("ma60", sa.Numeric(10, 2), nullable=True),
        sa.Column("ma120", sa.Numeric(10, 2), nullable=True),
        sa.Column("ma250", sa.Numeric(10, 2), nullable=True),
        sa.Column("macd_dif", sa.Numeric(10, 4), nullable=True),
        sa.Column("macd_dea", sa.Numeric(10, 4), nullable=True),
        sa.Column("macd_hist", sa.Numeric(10, 4), nullable=True),
        sa.Column("kdj_k", sa.Numeric(10, 4), nullable=True),
        sa.Column("kdj_d", sa.Numeric(10, 4), nullable=True),
        sa.Column("kdj_j", sa.Numeric(10, 4), nullable=True),
        sa.Column("rsi6", sa.Numeric(10, 4), nullable=True),
        sa.Column("rsi12", sa.Numeric(10, 4), nullable=True),
        sa.Column("rsi24", sa.Numeric(10, 4), nullable=True),
        sa.Column("boll_upper", sa.Numeric(10, 2), nullable=True),
        sa.Column("boll_mid", sa.Numeric(10, 2), nullable=True),
        sa.Column("boll_lower", sa.Numeric(10, 2), nullable=True),
        sa.Column("vol_ma5", sa.Numeric(20, 2), nullable=True),
        sa.Column("vol_ma10", sa.Numeric(20, 2), nullable=True),
        sa.Column("vol_ratio", sa.Numeric(10, 4), nullable=True),
        sa.Column("atr14", sa.Numeric(10, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("ts_code", "trade_date"),
    )
    op.create_index("idx_technical_code_date", "technical_daily", ["ts_code", sa.text("trade_date DESC")])
    op.create_index("idx_technical_trade_date", "technical_daily", ["trade_date"])

    # money_flow
    op.create_table(
        "money_flow",
        sa.Column("ts_code", sa.String(16), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("buy_sm_vol", sa.Numeric(20, 2), server_default="0"),
        sa.Column("buy_sm_amount", sa.Numeric(20, 2), server_default="0"),
        sa.Column("sell_sm_vol", sa.Numeric(20, 2), server_default="0"),
        sa.Column("sell_sm_amount", sa.Numeric(20, 2), server_default="0"),
        sa.Column("buy_md_vol", sa.Numeric(20, 2), server_default="0"),
        sa.Column("buy_md_amount", sa.Numeric(20, 2), server_default="0"),
        sa.Column("sell_md_vol", sa.Numeric(20, 2), server_default="0"),
        sa.Column("sell_md_amount", sa.Numeric(20, 2), server_default="0"),
        sa.Column("buy_lg_vol", sa.Numeric(20, 2), server_default="0"),
        sa.Column("buy_lg_amount", sa.Numeric(20, 2), server_default="0"),
        sa.Column("sell_lg_vol", sa.Numeric(20, 2), server_default="0"),
        sa.Column("sell_lg_amount", sa.Numeric(20, 2), server_default="0"),
        sa.Column("buy_elg_vol", sa.Numeric(20, 2), server_default="0"),
        sa.Column("buy_elg_amount", sa.Numeric(20, 2), server_default="0"),
        sa.Column("sell_elg_vol", sa.Numeric(20, 2), server_default="0"),
        sa.Column("sell_elg_amount", sa.Numeric(20, 2), server_default="0"),
        sa.Column("net_mf_amount", sa.Numeric(20, 2), server_default="0"),
        sa.Column("data_source", sa.String(16), nullable=False, server_default="akshare"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("ts_code", "trade_date"),
    )

    # dragon_tiger
    op.create_table(
        "dragon_tiger",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ts_code", sa.String(16), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.String(200), nullable=True),
        sa.Column("buy_total", sa.Numeric(20, 2), nullable=True),
        sa.Column("sell_total", sa.Numeric(20, 2), nullable=True),
        sa.Column("net_buy", sa.Numeric(20, 2), nullable=True),
        sa.Column("list_name", sa.String(100), nullable=True),
        sa.Column("data_source", sa.String(16), nullable=False, server_default="akshare"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_dragon_tiger_date", "dragon_tiger", ["trade_date"])
    op.create_index("idx_dragon_tiger_code", "dragon_tiger", ["ts_code", sa.text("trade_date DESC")])

    # strategies
    op.create_table(
        "strategies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(64), nullable=False, unique=True),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("params", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # data_source_configs
    op.create_table(
        "data_source_configs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_name", sa.String(32), nullable=False, unique=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("last_health_check", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # backtest_tasks
    op.create_table(
        "backtest_tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("strategy_id", sa.Integer(), sa.ForeignKey("strategies.id"), nullable=True),
        sa.Column("strategy_params", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("stock_codes", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("initial_capital", sa.Numeric(20, 2), nullable=False, server_default="1000000"),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # backtest_results
    op.create_table(
        "backtest_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("backtest_tasks.id"), nullable=False),
        sa.Column("total_return", sa.Numeric(10, 4), nullable=True),
        sa.Column("annual_return", sa.Numeric(10, 4), nullable=True),
        sa.Column("max_drawdown", sa.Numeric(10, 4), nullable=True),
        sa.Column("sharpe_ratio", sa.Numeric(10, 4), nullable=True),
        sa.Column("win_rate", sa.Numeric(10, 4), nullable=True),
        sa.Column("profit_loss_ratio", sa.Numeric(10, 4), nullable=True),
        sa.Column("total_trades", sa.Integer(), nullable=True),
        sa.Column("benchmark_return", sa.Numeric(10, 4), nullable=True),
        sa.Column("alpha", sa.Numeric(10, 4), nullable=True),
        sa.Column("beta", sa.Numeric(10, 4), nullable=True),
        sa.Column("volatility", sa.Numeric(10, 4), nullable=True),
        sa.Column("calmar_ratio", sa.Numeric(10, 4), nullable=True),
        sa.Column("sortino_ratio", sa.Numeric(10, 4), nullable=True),
        sa.Column("trades_json", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("equity_curve_json", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("backtest_results")
    op.drop_table("backtest_tasks")
    op.drop_table("data_source_configs")
    op.drop_table("strategies")
    op.drop_table("dragon_tiger")
    op.drop_table("money_flow")
    op.drop_table("technical_daily")
    op.drop_table("finance_indicator")
    op.drop_table("stock_min")
    op.drop_table("stock_daily")
    op.drop_table("stocks")
    op.drop_table("trade_calendar")
