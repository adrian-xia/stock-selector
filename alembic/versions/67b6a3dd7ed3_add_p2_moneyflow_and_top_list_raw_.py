"""add P2 moneyflow and top list raw tushare tables

Revision ID: 67b6a3dd7ed3
Revises: f4daf202054a
Create Date: 2026-02-16 20:22:56.965156

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '67b6a3dd7ed3'
down_revision: Union[str, Sequence[str], None] = 'f4daf202054a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. raw_tushare_moneyflow - 个股资金流向原始表
    op.create_table('raw_tushare_moneyflow',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    # 小单
    sa.Column('buy_sm_vol', sa.Numeric(precision=20, scale=0), nullable=True),
    sa.Column('buy_sm_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('sell_sm_vol', sa.Numeric(precision=20, scale=0), nullable=True),
    sa.Column('sell_sm_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    # 中单
    sa.Column('buy_md_vol', sa.Numeric(precision=20, scale=0), nullable=True),
    sa.Column('buy_md_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('sell_md_vol', sa.Numeric(precision=20, scale=0), nullable=True),
    sa.Column('sell_md_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    # 大单
    sa.Column('buy_lg_vol', sa.Numeric(precision=20, scale=0), nullable=True),
    sa.Column('buy_lg_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('sell_lg_vol', sa.Numeric(precision=20, scale=0), nullable=True),
    sa.Column('sell_lg_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    # 特大单
    sa.Column('buy_elg_vol', sa.Numeric(precision=20, scale=0), nullable=True),
    sa.Column('buy_elg_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('sell_elg_vol', sa.Numeric(precision=20, scale=0), nullable=True),
    sa.Column('sell_elg_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    # 净流入
    sa.Column('net_mf_vol', sa.Numeric(precision=20, scale=0), nullable=True),
    sa.Column('net_mf_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'trade_date')
    )
    op.create_index('idx_raw_moneyflow_trade_date', 'raw_tushare_moneyflow', ['trade_date'], unique=False)

    # 2. raw_tushare_moneyflow_dc - 个股资金流向原始表（东方财富）
    op.create_table('raw_tushare_moneyflow_dc',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    sa.Column('name', sa.String(length=32), nullable=True),
    sa.Column('pct_change', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('close', sa.Numeric(precision=12, scale=4), nullable=True),
    # 主力净流入
    sa.Column('net_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('net_amount_rate', sa.Numeric(precision=12, scale=4), nullable=True),
    # 超大单净流入
    sa.Column('buy_elg_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('buy_elg_amount_rate', sa.Numeric(precision=12, scale=4), nullable=True),
    # 大单净流入
    sa.Column('buy_lg_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('buy_lg_amount_rate', sa.Numeric(precision=12, scale=4), nullable=True),
    # 中单净流入
    sa.Column('buy_md_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('buy_md_amount_rate', sa.Numeric(precision=12, scale=4), nullable=True),
    # 小单净流入
    sa.Column('buy_sm_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('buy_sm_amount_rate', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'trade_date')
    )
    op.create_index('idx_raw_moneyflow_dc_trade_date', 'raw_tushare_moneyflow_dc', ['trade_date'], unique=False)

    # 3. raw_tushare_moneyflow_ths - 个股资金流向原始表（同花顺）
    op.create_table('raw_tushare_moneyflow_ths',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    sa.Column('name', sa.String(length=32), nullable=True),
    sa.Column('pct_change', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('latest', sa.Numeric(precision=12, scale=4), nullable=True),
    # 资金净流入
    sa.Column('net_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('net_d5_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    # 大单净流入
    sa.Column('buy_lg_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('buy_lg_amount_rate', sa.Numeric(precision=12, scale=4), nullable=True),
    # 中单净流入
    sa.Column('buy_md_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('buy_md_amount_rate', sa.Numeric(precision=12, scale=4), nullable=True),
    # 小单净流入
    sa.Column('buy_sm_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('buy_sm_amount_rate', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'trade_date')
    )
    op.create_index('idx_raw_moneyflow_ths_trade_date', 'raw_tushare_moneyflow_ths', ['trade_date'], unique=False)

    # 4. raw_tushare_moneyflow_hsgt - 沪深港通资金流向原始表
    op.create_table('raw_tushare_moneyflow_hsgt',
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    sa.Column('ggt_ss', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('ggt_sz', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('hgt', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('sgt', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('north_money', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('south_money', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('trade_date')
    )

    # 5. raw_tushare_moneyflow_ind_ths - 同花顺行业资金流向原始表
    op.create_table('raw_tushare_moneyflow_ind_ths',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    sa.Column('industry', sa.String(length=64), nullable=True),
    sa.Column('lead_stock', sa.String(length=32), nullable=True),
    sa.Column('close', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('pct_change', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('company_num', sa.Numeric(precision=10, scale=0), nullable=True),
    sa.Column('pct_change_stock', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('close_price', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('net_buy_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('net_sell_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('net_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'trade_date')
    )
    op.create_index('idx_raw_moneyflow_ind_ths_trade_date', 'raw_tushare_moneyflow_ind_ths', ['trade_date'], unique=False)

    # 6. raw_tushare_moneyflow_cnt_ths - 同花顺概念板块资金流向原始表
    op.create_table('raw_tushare_moneyflow_cnt_ths',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=True),
    sa.Column('lead_stock', sa.String(length=32), nullable=True),
    sa.Column('close_price', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('pct_change', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('industry_index', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('company_num', sa.Numeric(precision=10, scale=0), nullable=True),
    sa.Column('pct_change_stock', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('net_buy_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('net_sell_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('net_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'trade_date')
    )
    op.create_index('idx_raw_moneyflow_cnt_ths_trade_date', 'raw_tushare_moneyflow_cnt_ths', ['trade_date'], unique=False)

    # 7. raw_tushare_moneyflow_ind_dc - 东财概念及行业板块资金流向原始表
    op.create_table('raw_tushare_moneyflow_ind_dc',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    sa.Column('content_type', sa.String(length=16), nullable=True),
    sa.Column('name', sa.String(length=64), nullable=True),
    sa.Column('pct_change', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('close', sa.Numeric(precision=12, scale=4), nullable=True),
    # 主力净流入
    sa.Column('net_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('net_amount_rate', sa.Numeric(precision=12, scale=4), nullable=True),
    # 超大单净流入
    sa.Column('buy_elg_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('buy_elg_amount_rate', sa.Numeric(precision=12, scale=4), nullable=True),
    # 大单净流入
    sa.Column('buy_lg_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('buy_lg_amount_rate', sa.Numeric(precision=12, scale=4), nullable=True),
    # 中单净流入
    sa.Column('buy_md_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('buy_md_amount_rate', sa.Numeric(precision=12, scale=4), nullable=True),
    # 小单净流入
    sa.Column('buy_sm_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('buy_sm_amount_rate', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('buy_sm_amount_stock', sa.String(length=32), nullable=True),
    sa.Column('rank', sa.Numeric(precision=10, scale=0), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'trade_date')
    )
    op.create_index('idx_raw_moneyflow_ind_dc_trade_date', 'raw_tushare_moneyflow_ind_dc', ['trade_date'], unique=False)

    # 8. raw_tushare_moneyflow_mkt_dc - 大盘资金流向原始表（东方财富）
    op.create_table('raw_tushare_moneyflow_mkt_dc',
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    sa.Column('close_sh', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('pct_change_sh', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('close_sz', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('pct_change_sz', sa.Numeric(precision=12, scale=4), nullable=True),
    # 主力净流入
    sa.Column('net_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('net_amount_rate', sa.Numeric(precision=12, scale=4), nullable=True),
    # 超大单净流入
    sa.Column('buy_elg_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('buy_elg_amount_rate', sa.Numeric(precision=12, scale=4), nullable=True),
    # 大单净流入
    sa.Column('buy_lg_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('buy_lg_amount_rate', sa.Numeric(precision=12, scale=4), nullable=True),
    # 中单净流入
    sa.Column('buy_md_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('buy_md_amount_rate', sa.Numeric(precision=12, scale=4), nullable=True),
    # 小单净流入
    sa.Column('buy_sm_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('buy_sm_amount_rate', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('trade_date')
    )

    # 9. raw_tushare_top_list - 龙虎榜每日明细原始表
    op.create_table('raw_tushare_top_list',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    sa.Column('name', sa.String(length=32), nullable=True),
    sa.Column('close', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('pct_change', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('turnover_rate', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('amount', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('l_sell', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('l_buy', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('l_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('net_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('net_rate', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('amount_rate', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('float_values', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('reason', sa.String(length=256), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'trade_date')
    )
    op.create_index('idx_raw_top_list_trade_date', 'raw_tushare_top_list', ['trade_date'], unique=False)

    # 10. raw_tushare_top_inst - 龙虎榜机构明细原始表
    op.create_table('raw_tushare_top_inst',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    sa.Column('exalter', sa.String(length=128), nullable=False),
    sa.Column('side', sa.String(length=4), nullable=True),
    sa.Column('buy', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('buy_rate', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('sell', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('sell_rate', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('net_buy', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('reason', sa.String(length=256), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'trade_date', 'exalter')
    )
    op.create_index('idx_raw_top_inst_trade_date', 'raw_tushare_top_inst', ['trade_date'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # 删除 P2 原始表（按创建顺序的逆序）
    op.drop_index('idx_raw_top_inst_trade_date', table_name='raw_tushare_top_inst')
    op.drop_table('raw_tushare_top_inst')

    op.drop_index('idx_raw_top_list_trade_date', table_name='raw_tushare_top_list')
    op.drop_table('raw_tushare_top_list')

    op.drop_table('raw_tushare_moneyflow_mkt_dc')

    op.drop_index('idx_raw_moneyflow_ind_dc_trade_date', table_name='raw_tushare_moneyflow_ind_dc')
    op.drop_table('raw_tushare_moneyflow_ind_dc')

    op.drop_index('idx_raw_moneyflow_cnt_ths_trade_date', table_name='raw_tushare_moneyflow_cnt_ths')
    op.drop_table('raw_tushare_moneyflow_cnt_ths')

    op.drop_index('idx_raw_moneyflow_ind_ths_trade_date', table_name='raw_tushare_moneyflow_ind_ths')
    op.drop_table('raw_tushare_moneyflow_ind_ths')

    op.drop_table('raw_tushare_moneyflow_hsgt')

    op.drop_index('idx_raw_moneyflow_ths_trade_date', table_name='raw_tushare_moneyflow_ths')
    op.drop_table('raw_tushare_moneyflow_ths')

    op.drop_index('idx_raw_moneyflow_dc_trade_date', table_name='raw_tushare_moneyflow_dc')
    op.drop_table('raw_tushare_moneyflow_dc')

    op.drop_index('idx_raw_moneyflow_trade_date', table_name='raw_tushare_moneyflow')
    op.drop_table('raw_tushare_moneyflow')
