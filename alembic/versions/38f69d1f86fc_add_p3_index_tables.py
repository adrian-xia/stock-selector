"""add_p3_index_tables

Revision ID: 38f69d1f86fc
Revises: 67b6a3dd7ed3
Create Date: 2026-02-16 21:09:02.569411

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '38f69d1f86fc'
down_revision: Union[str, Sequence[str], None] = '67b6a3dd7ed3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # =====================================================================
    # P3 指数业务表（6 张）
    # =====================================================================

    # 1. index_basic - 指数基础信息表
    op.create_table(
        'index_basic',
        sa.Column('ts_code', sa.String(16), primary_key=True),
        sa.Column('name', sa.String(64), nullable=False),
        sa.Column('fullname', sa.String(128), nullable=True),
        sa.Column('market', sa.String(16), nullable=True),
        sa.Column('publisher', sa.String(64), nullable=True),
        sa.Column('index_type', sa.String(16), nullable=True),
        sa.Column('category', sa.String(16), nullable=True),
        sa.Column('base_date', sa.Date, nullable=True),
        sa.Column('base_point', sa.Numeric(12, 4), nullable=True),
        sa.Column('list_date', sa.Date, nullable=True),
        sa.Column('weight_rule', sa.String(128), nullable=True),
        sa.Column('desc', sa.String(512), nullable=True),
        sa.Column('exp_date', sa.Date, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # 2. index_daily - 指数日线行情表
    op.create_table(
        'index_daily',
        sa.Column('ts_code', sa.String(16), primary_key=True),
        sa.Column('trade_date', sa.Date, primary_key=True),
        sa.Column('open', sa.Numeric(12, 4), nullable=False),
        sa.Column('high', sa.Numeric(12, 4), nullable=False),
        sa.Column('low', sa.Numeric(12, 4), nullable=False),
        sa.Column('close', sa.Numeric(12, 4), nullable=False),
        sa.Column('pre_close', sa.Numeric(12, 4), nullable=True),
        sa.Column('change', sa.Numeric(12, 4), nullable=True),
        sa.Column('pct_chg', sa.Numeric(10, 4), nullable=True),
        sa.Column('vol', sa.Numeric(20, 2), nullable=False, server_default='0'),
        sa.Column('amount', sa.Numeric(20, 2), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('idx_index_daily_code_date', 'index_daily', ['ts_code', 'trade_date'], postgresql_ops={'trade_date': 'DESC'})
    op.create_index('idx_index_daily_trade_date', 'index_daily', ['trade_date'])

    # 3. index_weight - 指数成分股权重表
    op.create_table(
        'index_weight',
        sa.Column('index_code', sa.String(16), primary_key=True),
        sa.Column('con_code', sa.String(16), primary_key=True),
        sa.Column('trade_date', sa.Date, primary_key=True),
        sa.Column('weight', sa.Numeric(10, 4), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('idx_index_weight_index_code', 'index_weight', ['index_code'])
    op.create_index('idx_index_weight_trade_date', 'index_weight', ['trade_date'])
    op.create_index('idx_index_weight_con_code', 'index_weight', ['con_code'])

    # 4. industry_classify - 行业分类表
    op.create_table(
        'industry_classify',
        sa.Column('index_code', sa.String(16), primary_key=True),
        sa.Column('industry_name', sa.String(64), nullable=False),
        sa.Column('level', sa.String(4), nullable=False),
        sa.Column('industry_code', sa.String(16), nullable=True),
        sa.Column('src', sa.String(16), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # 5. industry_member - 行业成分股表
    op.create_table(
        'industry_member',
        sa.Column('index_code', sa.String(16), primary_key=True),
        sa.Column('con_code', sa.String(16), primary_key=True),
        sa.Column('in_date', sa.Date, primary_key=True),
        sa.Column('out_date', sa.Date, nullable=True),
        sa.Column('is_new', sa.String(4), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('idx_industry_member_index_code', 'industry_member', ['index_code'])
    op.create_index('idx_industry_member_con_code', 'industry_member', ['con_code'])
    op.create_index('idx_industry_member_in_date', 'industry_member', ['in_date'])

    # __CONTINUE_HERE__
    # 6. index_technical_daily - 指数技术指标表
    op.create_table(
        'index_technical_daily',
        sa.Column('ts_code', sa.String(16), primary_key=True),
        sa.Column('trade_date', sa.Date, primary_key=True),
        # 均线指标
        sa.Column('ma5', sa.Numeric(12, 4), nullable=True),
        sa.Column('ma10', sa.Numeric(12, 4), nullable=True),
        sa.Column('ma20', sa.Numeric(12, 4), nullable=True),
        sa.Column('ma60', sa.Numeric(12, 4), nullable=True),
        sa.Column('ma120', sa.Numeric(12, 4), nullable=True),
        sa.Column('ma250', sa.Numeric(12, 4), nullable=True),
        # MACD 指标
        sa.Column('macd_dif', sa.Numeric(12, 4), nullable=True),
        sa.Column('macd_dea', sa.Numeric(12, 4), nullable=True),
        sa.Column('macd_hist', sa.Numeric(12, 4), nullable=True),
        # KDJ 指标
        sa.Column('kdj_k', sa.Numeric(12, 4), nullable=True),
        sa.Column('kdj_d', sa.Numeric(12, 4), nullable=True),
        sa.Column('kdj_j', sa.Numeric(12, 4), nullable=True),
        # RSI 指标
        sa.Column('rsi6', sa.Numeric(12, 4), nullable=True),
        sa.Column('rsi12', sa.Numeric(12, 4), nullable=True),
        sa.Column('rsi24', sa.Numeric(12, 4), nullable=True),
        # 布林带指标
        sa.Column('boll_upper', sa.Numeric(12, 4), nullable=True),
        sa.Column('boll_mid', sa.Numeric(12, 4), nullable=True),
        sa.Column('boll_lower', sa.Numeric(12, 4), nullable=True),
        # 成交量指标
        sa.Column('vol_ma5', sa.Numeric(20, 2), nullable=True),
        sa.Column('vol_ma10', sa.Numeric(20, 2), nullable=True),
        sa.Column('vol_ratio', sa.Numeric(12, 4), nullable=True),
        # 其他指标
        sa.Column('atr14', sa.Numeric(12, 4), nullable=True),
        sa.Column('cci14', sa.Numeric(12, 4), nullable=True),
        sa.Column('willr14', sa.Numeric(12, 4), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('idx_index_technical_code_date', 'index_technical_daily', ['ts_code', 'trade_date'], postgresql_ops={'trade_date': 'DESC'})
    op.create_index('idx_index_technical_trade_date', 'index_technical_daily', ['trade_date'])

    # =====================================================================
    # P3 指数原始表（16 张）
    # =====================================================================

    # 1. raw_tushare_index_basic - 指数基础信息原始表
    op.create_table(
        'raw_tushare_index_basic',
        sa.Column('ts_code', sa.String(16), primary_key=True),
        sa.Column('name', sa.String(64), nullable=True),
        sa.Column('fullname', sa.String(128), nullable=True),
        sa.Column('market', sa.String(16), nullable=True),
        sa.Column('publisher', sa.String(64), nullable=True),
        sa.Column('index_type', sa.String(16), nullable=True),
        sa.Column('category', sa.String(16), nullable=True),
        sa.Column('base_date', sa.String(8), nullable=True),
        sa.Column('base_point', sa.Numeric(12, 4), nullable=True),
        sa.Column('list_date', sa.String(8), nullable=True),
        sa.Column('weight_rule', sa.String(128), nullable=True),
        sa.Column('desc', sa.String(512), nullable=True),
        sa.Column('exp_date', sa.String(8), nullable=True),
        sa.Column('fetched_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # __CONTINUE_HERE__
    # 2. raw_tushare_index_weight - 指数成分股权重原始表
    op.create_table(
        'raw_tushare_index_weight',
        sa.Column('index_code', sa.String(16), primary_key=True),
        sa.Column('con_code', sa.String(16), primary_key=True),
        sa.Column('trade_date', sa.String(8), primary_key=True),
        sa.Column('weight', sa.Numeric(10, 4), nullable=True),
        sa.Column('fetched_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_raw_index_weight_index_code', 'raw_tushare_index_weight', ['index_code'])
    op.create_index('idx_raw_index_weight_trade_date', 'raw_tushare_index_weight', ['trade_date'])

    # 3. raw_tushare_index_daily - 指数日线行情原始表
    op.create_table(
        'raw_tushare_index_daily',
        sa.Column('ts_code', sa.String(16), primary_key=True),
        sa.Column('trade_date', sa.String(8), primary_key=True),
        sa.Column('open', sa.Numeric(12, 4), nullable=True),
        sa.Column('high', sa.Numeric(12, 4), nullable=True),
        sa.Column('low', sa.Numeric(12, 4), nullable=True),
        sa.Column('close', sa.Numeric(12, 4), nullable=True),
        sa.Column('pre_close', sa.Numeric(12, 4), nullable=True),
        sa.Column('change', sa.Numeric(12, 4), nullable=True),
        sa.Column('pct_chg', sa.Numeric(10, 4), nullable=True),
        sa.Column('vol', sa.Numeric(20, 2), nullable=True),
        sa.Column('amount', sa.Numeric(20, 2), nullable=True),
        sa.Column('fetched_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_raw_index_daily_trade_date', 'raw_tushare_index_daily', ['trade_date'])

    # 4. raw_tushare_index_weekly - 指数周线行情原始表
    op.create_table(
        'raw_tushare_index_weekly',
        sa.Column('ts_code', sa.String(16), primary_key=True),
        sa.Column('trade_date', sa.String(8), primary_key=True),
        sa.Column('open', sa.Numeric(12, 4), nullable=True),
        sa.Column('high', sa.Numeric(12, 4), nullable=True),
        sa.Column('low', sa.Numeric(12, 4), nullable=True),
        sa.Column('close', sa.Numeric(12, 4), nullable=True),
        sa.Column('pre_close', sa.Numeric(12, 4), nullable=True),
        sa.Column('change', sa.Numeric(12, 4), nullable=True),
        sa.Column('pct_chg', sa.Numeric(10, 4), nullable=True),
        sa.Column('vol', sa.Numeric(20, 2), nullable=True),
        sa.Column('amount', sa.Numeric(20, 2), nullable=True),
        sa.Column('fetched_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_raw_index_weekly_trade_date', 'raw_tushare_index_weekly', ['trade_date'])

    # 5. raw_tushare_index_monthly - 指数月线行情原始表
    op.create_table(
        'raw_tushare_index_monthly',
        sa.Column('ts_code', sa.String(16), primary_key=True),
        sa.Column('trade_date', sa.String(8), primary_key=True),
        sa.Column('open', sa.Numeric(12, 4), nullable=True),
        sa.Column('high', sa.Numeric(12, 4), nullable=True),
        sa.Column('low', sa.Numeric(12, 4), nullable=True),
        sa.Column('close', sa.Numeric(12, 4), nullable=True),
        sa.Column('pre_close', sa.Numeric(12, 4), nullable=True),
        sa.Column('change', sa.Numeric(12, 4), nullable=True),
        sa.Column('pct_chg', sa.Numeric(10, 4), nullable=True),
        sa.Column('vol', sa.Numeric(20, 2), nullable=True),
        sa.Column('amount', sa.Numeric(20, 2), nullable=True),
        sa.Column('fetched_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_raw_index_monthly_trade_date', 'raw_tushare_index_monthly', ['trade_date'])

    # 6. raw_tushare_index_dailybasic - 指数每日指标原始表
    op.create_table(
        'raw_tushare_index_dailybasic',
        sa.Column('ts_code', sa.String(16), primary_key=True),
        sa.Column('trade_date', sa.String(8), primary_key=True),
        sa.Column('total_mv', sa.Numeric(20, 4), nullable=True),
        sa.Column('float_mv', sa.Numeric(20, 4), nullable=True),
        sa.Column('total_share', sa.Numeric(20, 4), nullable=True),
        sa.Column('float_share', sa.Numeric(20, 4), nullable=True),
        sa.Column('free_share', sa.Numeric(20, 4), nullable=True),
        sa.Column('turnover_rate', sa.Numeric(12, 4), nullable=True),
        sa.Column('turnover_rate_f', sa.Numeric(12, 4), nullable=True),
        sa.Column('pe', sa.Numeric(16, 4), nullable=True),
        sa.Column('pe_ttm', sa.Numeric(16, 4), nullable=True),
        sa.Column('pb', sa.Numeric(16, 4), nullable=True),
        sa.Column('fetched_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_raw_index_dailybasic_trade_date', 'raw_tushare_index_dailybasic', ['trade_date'])

    # 7. raw_tushare_index_global - 国际指数行情原始表
    op.create_table(
        'raw_tushare_index_global',
        sa.Column('ts_code', sa.String(16), primary_key=True),
        sa.Column('trade_date', sa.String(8), primary_key=True),
        sa.Column('open', sa.Numeric(12, 4), nullable=True),
        sa.Column('high', sa.Numeric(12, 4), nullable=True),
        sa.Column('low', sa.Numeric(12, 4), nullable=True),
        sa.Column('close', sa.Numeric(12, 4), nullable=True),
        sa.Column('pre_close', sa.Numeric(12, 4), nullable=True),
        sa.Column('change', sa.Numeric(12, 4), nullable=True),
        sa.Column('pct_chg', sa.Numeric(10, 4), nullable=True),
        sa.Column('fetched_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_raw_index_global_trade_date', 'raw_tushare_index_global', ['trade_date'])

    # 8. raw_tushare_daily_info - 大盘每日指标原始表
    op.create_table(
        'raw_tushare_daily_info',
        sa.Column('trade_date', sa.String(8), primary_key=True),
        sa.Column('ts_code', sa.String(16), primary_key=True),
        sa.Column('ts_name', sa.String(32), nullable=True),
        sa.Column('com_count', sa.Numeric(10, 0), nullable=True),
        sa.Column('total_share', sa.Numeric(20, 4), nullable=True),
        sa.Column('float_share', sa.Numeric(20, 4), nullable=True),
        sa.Column('total_mv', sa.Numeric(20, 4), nullable=True),
        sa.Column('float_mv', sa.Numeric(20, 4), nullable=True),
        sa.Column('amount', sa.Numeric(20, 4), nullable=True),
        sa.Column('vol', sa.Numeric(20, 4), nullable=True),
        sa.Column('trans_count', sa.Numeric(20, 0), nullable=True),
        sa.Column('pe', sa.Numeric(16, 4), nullable=True),
        sa.Column('tr', sa.Numeric(12, 4), nullable=True),
        sa.Column('exchange', sa.String(8), nullable=True),
        sa.Column('fetched_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # 9. raw_tushare_sz_daily_info - 深圳市场每日指标原始表
    op.create_table(
        'raw_tushare_sz_daily_info',
        sa.Column('trade_date', sa.String(8), primary_key=True),
        sa.Column('ts_code', sa.String(16), primary_key=True),
        sa.Column('ts_name', sa.String(32), nullable=True),
        sa.Column('com_count', sa.Numeric(10, 0), nullable=True),
        sa.Column('total_share', sa.Numeric(20, 4), nullable=True),
        sa.Column('float_share', sa.Numeric(20, 4), nullable=True),
        sa.Column('total_mv', sa.Numeric(20, 4), nullable=True),
        sa.Column('float_mv', sa.Numeric(20, 4), nullable=True),
        sa.Column('amount', sa.Numeric(20, 4), nullable=True),
        sa.Column('vol', sa.Numeric(20, 4), nullable=True),
        sa.Column('trans_count', sa.Numeric(20, 0), nullable=True),
        sa.Column('pe', sa.Numeric(16, 4), nullable=True),
        sa.Column('tr', sa.Numeric(12, 4), nullable=True),
        sa.Column('fetched_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # 10. raw_tushare_index_classify - 申万行业分类原始表
    op.create_table(
        'raw_tushare_index_classify',
        sa.Column('index_code', sa.String(16), primary_key=True),
        sa.Column('industry_name', sa.String(64), nullable=True),
        sa.Column('level', sa.String(4), nullable=True),
        sa.Column('industry_code', sa.String(16), nullable=True),
        sa.Column('src', sa.String(16), nullable=True),
        sa.Column('parent_code', sa.String(16), nullable=True),
        sa.Column('fetched_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # 11. raw_tushare_index_member_all - 申万行业成分股原始表
    op.create_table(
        'raw_tushare_index_member_all',
        sa.Column('index_code', sa.String(16), primary_key=True),
        sa.Column('con_code', sa.String(16), primary_key=True),
        sa.Column('in_date', sa.String(8), primary_key=True),
        sa.Column('out_date', sa.String(8), nullable=True),
        sa.Column('is_new', sa.String(4), nullable=True),
        sa.Column('fetched_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_raw_index_member_all_index_code', 'raw_tushare_index_member_all', ['index_code'])
    op.create_index('idx_raw_index_member_all_in_date', 'raw_tushare_index_member_all', ['in_date'])

    # 12. raw_tushare_sw_daily - 申万行业日线行情原始表
    op.create_table(
        'raw_tushare_sw_daily',
        sa.Column('ts_code', sa.String(16), primary_key=True),
        sa.Column('trade_date', sa.String(8), primary_key=True),
        sa.Column('open', sa.Numeric(12, 4), nullable=True),
        sa.Column('high', sa.Numeric(12, 4), nullable=True),
        sa.Column('low', sa.Numeric(12, 4), nullable=True),
        sa.Column('close', sa.Numeric(12, 4), nullable=True),
        sa.Column('change', sa.Numeric(12, 4), nullable=True),
        sa.Column('pct_chg', sa.Numeric(10, 4), nullable=True),
        sa.Column('vol', sa.Numeric(20, 2), nullable=True),
        sa.Column('amount', sa.Numeric(20, 2), nullable=True),
        sa.Column('fetched_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_raw_sw_daily_trade_date', 'raw_tushare_sw_daily', ['trade_date'])

    # 13. raw_tushare_ci_index_member - 中信行业成分股原始表
    op.create_table(
        'raw_tushare_ci_index_member',
        sa.Column('index_code', sa.String(16), primary_key=True),
        sa.Column('con_code', sa.String(16), primary_key=True),
        sa.Column('in_date', sa.String(8), primary_key=True),
        sa.Column('out_date', sa.String(8), nullable=True),
        sa.Column('is_new', sa.String(4), nullable=True),
        sa.Column('fetched_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_raw_ci_index_member_index_code', 'raw_tushare_ci_index_member', ['index_code'])
    op.create_index('idx_raw_ci_index_member_in_date', 'raw_tushare_ci_index_member', ['in_date'])

    # 14. raw_tushare_ci_daily - 中信行业日线行情原始表
    op.create_table(
        'raw_tushare_ci_daily',
        sa.Column('ts_code', sa.String(16), primary_key=True),
        sa.Column('trade_date', sa.String(8), primary_key=True),
        sa.Column('open', sa.Numeric(12, 4), nullable=True),
        sa.Column('high', sa.Numeric(12, 4), nullable=True),
        sa.Column('low', sa.Numeric(12, 4), nullable=True),
        sa.Column('close', sa.Numeric(12, 4), nullable=True),
        sa.Column('change', sa.Numeric(12, 4), nullable=True),
        sa.Column('pct_chg', sa.Numeric(10, 4), nullable=True),
        sa.Column('vol', sa.Numeric(20, 2), nullable=True),
        sa.Column('amount', sa.Numeric(20, 2), nullable=True),
        sa.Column('fetched_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_raw_ci_daily_trade_date', 'raw_tushare_ci_daily', ['trade_date'])

    # 15. raw_tushare_index_factor_pro - 指数技术面因子原始表
    op.create_table(
        'raw_tushare_index_factor_pro',
        sa.Column('ts_code', sa.String(16), primary_key=True),
        sa.Column('trade_date', sa.String(8), primary_key=True),
        # 均线指标
        sa.Column('ma5', sa.Numeric(12, 4), nullable=True),
        sa.Column('ma10', sa.Numeric(12, 4), nullable=True),
        sa.Column('ma20', sa.Numeric(12, 4), nullable=True),
        sa.Column('ma60', sa.Numeric(12, 4), nullable=True),
        sa.Column('ma120', sa.Numeric(12, 4), nullable=True),
        sa.Column('ma250', sa.Numeric(12, 4), nullable=True),
        # MACD 指标
        sa.Column('macd_dif', sa.Numeric(12, 4), nullable=True),
        sa.Column('macd_dea', sa.Numeric(12, 4), nullable=True),
        sa.Column('macd', sa.Numeric(12, 4), nullable=True),
        # KDJ 指标
        sa.Column('kdj_k', sa.Numeric(12, 4), nullable=True),
        sa.Column('kdj_d', sa.Numeric(12, 4), nullable=True),
        sa.Column('kdj_j', sa.Numeric(12, 4), nullable=True),
        # RSI 指标
        sa.Column('rsi6', sa.Numeric(12, 4), nullable=True),
        sa.Column('rsi12', sa.Numeric(12, 4), nullable=True),
        sa.Column('rsi24', sa.Numeric(12, 4), nullable=True),
        # 布林带指标
        sa.Column('boll_upper', sa.Numeric(12, 4), nullable=True),
        sa.Column('boll_mid', sa.Numeric(12, 4), nullable=True),
        sa.Column('boll_lower', sa.Numeric(12, 4), nullable=True),
        # 其他指标
        sa.Column('atr', sa.Numeric(12, 4), nullable=True),
        sa.Column('cci', sa.Numeric(12, 4), nullable=True),
        sa.Column('wr', sa.Numeric(12, 4), nullable=True),
        sa.Column('fetched_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_raw_index_factor_pro_trade_date', 'raw_tushare_index_factor_pro', ['trade_date'])

    # 16. raw_tushare_tdx_daily - 通达信日线行情原始表
    op.create_table(
        'raw_tushare_tdx_daily',
        sa.Column('ts_code', sa.String(16), primary_key=True),
        sa.Column('trade_date', sa.String(8), primary_key=True),
        sa.Column('open', sa.Numeric(12, 4), nullable=True),
        sa.Column('high', sa.Numeric(12, 4), nullable=True),
        sa.Column('low', sa.Numeric(12, 4), nullable=True),
        sa.Column('close', sa.Numeric(12, 4), nullable=True),
        sa.Column('pre_close', sa.Numeric(12, 4), nullable=True),
        sa.Column('change', sa.Numeric(12, 4), nullable=True),
        sa.Column('pct_chg', sa.Numeric(10, 4), nullable=True),
        sa.Column('vol', sa.Numeric(20, 2), nullable=True),
        sa.Column('amount', sa.Numeric(20, 2), nullable=True),
        sa.Column('fetched_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_raw_tdx_daily_trade_date', 'raw_tushare_tdx_daily', ['trade_date'])


def downgrade() -> None:
    """Downgrade schema."""
    # 删除 P3 指数原始表（16 张）
    op.drop_table('raw_tushare_tdx_daily')
    op.drop_table('raw_tushare_index_factor_pro')
    op.drop_table('raw_tushare_ci_daily')
    op.drop_table('raw_tushare_ci_index_member')
    op.drop_table('raw_tushare_sw_daily')
    op.drop_table('raw_tushare_index_member_all')
    op.drop_table('raw_tushare_index_classify')
    op.drop_table('raw_tushare_sz_daily_info')
    op.drop_table('raw_tushare_daily_info')
    op.drop_table('raw_tushare_index_global')
    op.drop_table('raw_tushare_index_dailybasic')
    op.drop_table('raw_tushare_index_monthly')
    op.drop_table('raw_tushare_index_weekly')
    op.drop_table('raw_tushare_index_daily')
    op.drop_table('raw_tushare_index_weight')
    op.drop_table('raw_tushare_index_basic')

    # 删除 P3 指数业务表（6 张）
    op.drop_table('index_technical_daily')
    op.drop_table('industry_member')
    op.drop_table('industry_classify')
    op.drop_table('index_weight')
    op.drop_table('index_daily')
    op.drop_table('index_basic')
