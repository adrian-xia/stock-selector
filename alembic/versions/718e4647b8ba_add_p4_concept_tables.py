"""add_p4_concept_tables

Revision ID: 718e4647b8ba
Revises: 38f69d1f86fc
Create Date: 2026-02-16 21:38:07.223918

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '718e4647b8ba'
down_revision: Union[str, Sequence[str], None] = '38f69d1f86fc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # =====================================================================
    # 4 张板块业务表
    # =====================================================================

    # 1. concept_index（板块基础信息表）
    op.create_table(
        'concept_index',
        sa.Column('ts_code', sa.String(16), nullable=False),
        sa.Column('name', sa.String(64), nullable=False),
        sa.Column('src', sa.String(16), nullable=False),
        sa.Column('type', sa.String(16), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('ts_code')
    )

    # 2. concept_daily（板块日线行情表）
    op.create_table(
        'concept_daily',
        sa.Column('ts_code', sa.String(16), nullable=False),
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('open', sa.Numeric(12, 4), nullable=True),
        sa.Column('high', sa.Numeric(12, 4), nullable=True),
        sa.Column('low', sa.Numeric(12, 4), nullable=True),
        sa.Column('close', sa.Numeric(12, 4), nullable=False),
        sa.Column('pre_close', sa.Numeric(12, 4), nullable=True),
        sa.Column('change', sa.Numeric(12, 4), nullable=True),
        sa.Column('pct_chg', sa.Numeric(10, 4), nullable=True),
        sa.Column('vol', sa.Numeric(20, 2), nullable=True),
        sa.Column('amount', sa.Numeric(20, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('ts_code', 'trade_date')
    )
    op.create_index('idx_concept_daily_code_date', 'concept_daily', ['ts_code', sa.text('trade_date DESC')])
    op.create_index('idx_concept_daily_trade_date', 'concept_daily', ['trade_date'])

    # 3. concept_member（板块成分股表）
    op.create_table(
        'concept_member',
        sa.Column('concept_code', sa.String(16), nullable=False),
        sa.Column('stock_code', sa.String(16), nullable=False),
        sa.Column('in_date', sa.Date(), nullable=False),
        sa.Column('out_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('concept_code', 'stock_code', 'in_date')
    )
    op.create_index('idx_concept_member_concept_code', 'concept_member', ['concept_code'])
    op.create_index('idx_concept_member_stock_code', 'concept_member', ['stock_code'])
    op.create_index('idx_concept_member_in_date', 'concept_member', ['in_date'])

    # 4. concept_technical_daily（板块技术指标表）
    op.create_table(
        'concept_technical_daily',
        sa.Column('ts_code', sa.String(16), nullable=False),
        sa.Column('trade_date', sa.Date(), nullable=False),
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
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('ts_code', 'trade_date')
    )
    op.create_index('idx_concept_technical_code_date', 'concept_technical_daily', ['ts_code', sa.text('trade_date DESC')])
    op.create_index('idx_concept_technical_trade_date', 'concept_technical_daily', ['trade_date'])

    # =====================================================================
    # 8 张板块原始表
    # =====================================================================

    # 1. raw_tushare_ths_index（同花顺板块指数）
    op.create_table(
        'raw_tushare_ths_index',
        sa.Column('ts_code', sa.String(16), nullable=False),
        sa.Column('name', sa.String(64), nullable=True),
        sa.Column('count', sa.Integer(), nullable=True),
        sa.Column('exchange', sa.String(16), nullable=True),
        sa.Column('list_date', sa.String(8), nullable=True),
        sa.Column('type', sa.String(16), nullable=True),
        sa.Column('fetched_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('ts_code')
    )

    # 2. raw_tushare_ths_daily（同花顺板块日线）
    op.create_table(
        'raw_tushare_ths_daily',
        sa.Column('ts_code', sa.String(16), nullable=False),
        sa.Column('trade_date', sa.String(8), nullable=False),
        sa.Column('open', sa.Numeric(12, 4), nullable=True),
        sa.Column('high', sa.Numeric(12, 4), nullable=True),
        sa.Column('low', sa.Numeric(12, 4), nullable=True),
        sa.Column('close', sa.Numeric(12, 4), nullable=True),
        sa.Column('pre_close', sa.Numeric(12, 4), nullable=True),
        sa.Column('change', sa.Numeric(12, 4), nullable=True),
        sa.Column('pct_chg', sa.Numeric(10, 4), nullable=True),
        sa.Column('vol', sa.Numeric(20, 2), nullable=True),
        sa.Column('amount', sa.Numeric(20, 2), nullable=True),
        sa.Column('fetched_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('ts_code', 'trade_date')
    )
    op.create_index('idx_raw_ths_daily_code_date', 'raw_tushare_ths_daily', ['ts_code', 'trade_date'])
    op.create_index('idx_raw_ths_daily_trade_date', 'raw_tushare_ths_daily', ['trade_date'])

    # 3. raw_tushare_ths_member（同花顺板块成分股）
    op.create_table(
        'raw_tushare_ths_member',
        sa.Column('ts_code', sa.String(16), nullable=False),
        sa.Column('code', sa.String(16), nullable=False),
        sa.Column('name', sa.String(64), nullable=True),
        sa.Column('weight', sa.Numeric(10, 4), nullable=True),
        sa.Column('in_date', sa.String(8), nullable=True),
        sa.Column('out_date', sa.String(8), nullable=True),
        sa.Column('is_new', sa.String(1), nullable=True),
        sa.Column('fetched_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('ts_code', 'code')
    )
    op.create_index('idx_raw_ths_member_ts_code', 'raw_tushare_ths_member', ['ts_code'])
    op.create_index('idx_raw_ths_member_code', 'raw_tushare_ths_member', ['code'])

    # 4. raw_tushare_dc_index（东方财富板块指数）
    op.create_table(
        'raw_tushare_dc_index',
        sa.Column('ts_code', sa.String(16), nullable=False),
        sa.Column('name', sa.String(64), nullable=True),
        sa.Column('src', sa.String(16), nullable=True),
        sa.Column('fetched_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('ts_code')
    )

    # 5. raw_tushare_dc_member（东方财富板块成分股）
    op.create_table(
        'raw_tushare_dc_member',
        sa.Column('ts_code', sa.String(16), nullable=False),
        sa.Column('code', sa.String(16), nullable=False),
        sa.Column('name', sa.String(64), nullable=True),
        sa.Column('in_date', sa.String(8), nullable=True),
        sa.Column('out_date', sa.String(8), nullable=True),
        sa.Column('fetched_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('ts_code', 'code')
    )
    op.create_index('idx_raw_dc_member_ts_code', 'raw_tushare_dc_member', ['ts_code'])
    op.create_index('idx_raw_dc_member_code', 'raw_tushare_dc_member', ['code'])

    # 6. raw_tushare_dc_hot_new（东方财富热门板块）
    op.create_table(
        'raw_tushare_dc_hot_new',
        sa.Column('ts_code', sa.String(16), nullable=False),
        sa.Column('trade_date', sa.String(8), nullable=False),
        sa.Column('name', sa.String(64), nullable=True),
        sa.Column('pct_chg', sa.Numeric(10, 4), nullable=True),
        sa.Column('rank', sa.Integer(), nullable=True),
        sa.Column('fetched_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('ts_code', 'trade_date')
    )
    op.create_index('idx_raw_dc_hot_new_ts_code', 'raw_tushare_dc_hot_new', ['ts_code'])
    op.create_index('idx_raw_dc_hot_new_trade_date', 'raw_tushare_dc_hot_new', ['trade_date'])

    # 7. raw_tushare_tdx_index（通达信板块指数）
    op.create_table(
        'raw_tushare_tdx_index',
        sa.Column('ts_code', sa.String(16), nullable=False),
        sa.Column('name', sa.String(64), nullable=True),
        sa.Column('market', sa.String(16), nullable=True),
        sa.Column('fetched_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('ts_code')
    )

    # 8. raw_tushare_tdx_member（通达信板块成分股）
    op.create_table(
        'raw_tushare_tdx_member',
        sa.Column('ts_code', sa.String(16), nullable=False),
        sa.Column('code', sa.String(16), nullable=False),
        sa.Column('name', sa.String(64), nullable=True),
        sa.Column('fetched_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('ts_code', 'code')
    )
    op.create_index('idx_raw_tdx_member_ts_code', 'raw_tushare_tdx_member', ['ts_code'])
    op.create_index('idx_raw_tdx_member_code', 'raw_tushare_tdx_member', ['code'])


def downgrade() -> None:
    """Downgrade schema."""
    # 删除 8 张原始表（逆序）
    op.drop_table('raw_tushare_tdx_member')
    op.drop_table('raw_tushare_tdx_index')
    op.drop_table('raw_tushare_dc_hot_new')
    op.drop_table('raw_tushare_dc_member')
    op.drop_table('raw_tushare_dc_index')
    op.drop_table('raw_tushare_ths_member')
    op.drop_table('raw_tushare_ths_daily')
    op.drop_table('raw_tushare_ths_index')

    # 删除 4 张业务表（逆序）
    op.drop_table('concept_technical_daily')
    op.drop_table('concept_member')
    op.drop_table('concept_daily')
    op.drop_table('concept_index')
