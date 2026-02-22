"""为 P0-P2 核心 raw 表补充 (ts_code, trade_date) 复合索引

优化 ETL 阶段的查询性能，当前这些表仅有 trade_date 单列索引。

Revision ID: e2f3a4b5c6d7
Revises: d1a2b3c4e5f6
Create Date: 2026-02-22
"""

from alembic import op

revision = "e2f3a4b5c6d7"
down_revision = "d1a2b3c4e5f6"
branch_labels = None
depends_on = None

# 需要补充复合索引的 raw 表（P0-P2 核心表，ETL 高频查询）
RAW_TABLES_WITH_COMPOSITE_INDEX = [
    # P0 基础行情
    ("raw_tushare_daily", "ts_code", "trade_date"),
    ("raw_tushare_adj_factor", "ts_code", "trade_date"),
    ("raw_tushare_daily_basic", "ts_code", "trade_date"),
    ("raw_tushare_stk_limit", "ts_code", "trade_date"),
    # P2 资金流向
    ("raw_tushare_moneyflow", "ts_code", "trade_date"),
    ("raw_tushare_moneyflow_dc", "ts_code", "trade_date"),
    ("raw_tushare_moneyflow_ths", "ts_code", "trade_date"),
    ("raw_tushare_moneyflow_ind_ths", "ts_code", "trade_date"),
    ("raw_tushare_moneyflow_cnt_ths", "ts_code", "trade_date"),
    ("raw_tushare_moneyflow_ind_dc", "ts_code", "trade_date"),
    ("raw_tushare_top_list", "ts_code", "trade_date"),
    # P3 指数日线
    ("raw_tushare_index_daily", "ts_code", "trade_date"),
    ("raw_tushare_index_factor_pro", "ts_code", "trade_date"),
]


def upgrade() -> None:
    for table_name, col1, col2 in RAW_TABLES_WITH_COMPOSITE_INDEX:
        idx_name = f"idx_{table_name.replace('raw_tushare_', 'raw_')}_code_date"
        op.create_index(
            idx_name,
            table_name,
            [col1, col2],
            if_not_exists=True,
        )


def downgrade() -> None:
    for table_name, _, _ in RAW_TABLES_WITH_COMPOSITE_INDEX:
        idx_name = f"idx_{table_name.replace('raw_tushare_', 'raw_')}_code_date"
        op.drop_index(idx_name, table_name=table_name, if_exists=True)
