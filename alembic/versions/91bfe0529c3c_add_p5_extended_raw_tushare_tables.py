"""add P5 extended raw tushare tables

Revision ID: 91bfe0529c3c
Revises: 718e4647b8ba
Create Date: 2026-02-16 22:13:06.711125

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '91bfe0529c3c'
down_revision: Union[str, Sequence[str], None] = '718e4647b8ba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # =====================================================================
    # 11a. 基础数据补充（7 张）
    # =====================================================================

    # 1. raw_tushare_namechange - 股票曾用名原始表
    op.create_table('raw_tushare_namechange',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('start_date', sa.String(length=8), nullable=False),
    sa.Column('end_date', sa.String(length=8), nullable=True),
    sa.Column('ann_date', sa.String(length=8), nullable=True),
    sa.Column('change_reason', sa.String(length=128), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'name', 'start_date')
    )
    op.create_index('idx_raw_namechange_ts_code', 'raw_tushare_namechange', ['ts_code'])
    op.create_index('idx_raw_namechange_start_date', 'raw_tushare_namechange', ['start_date'])

    # 2. raw_tushare_stock_company - 上市公司基本信息原始表
    op.create_table('raw_tushare_stock_company',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('exchange', sa.String(length=16), nullable=True),
    sa.Column('chairman', sa.String(length=64), nullable=True),
    sa.Column('manager', sa.String(length=64), nullable=True),
    sa.Column('secretary', sa.String(length=64), nullable=True),
    sa.Column('reg_capital', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('setup_date', sa.String(length=8), nullable=True),
    sa.Column('province', sa.String(length=32), nullable=True),
    sa.Column('city', sa.String(length=32), nullable=True),
    sa.Column('introduction', sa.Text(), nullable=True),
    sa.Column('website', sa.String(length=128), nullable=True),
    sa.Column('email', sa.String(length=64), nullable=True),
    sa.Column('office', sa.String(length=256), nullable=True),
    sa.Column('employees', sa.Integer(), nullable=True),
    sa.Column('main_business', sa.Text(), nullable=True),
    sa.Column('business_scope', sa.Text(), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code')
    )

    # 3. raw_tushare_stk_managers - 上市公司管理层原始表
    op.create_table('raw_tushare_stk_managers',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('ann_date', sa.String(length=8), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('gender', sa.String(length=8), nullable=True),
    sa.Column('lev', sa.String(length=32), nullable=True),
    sa.Column('title', sa.String(length=64), nullable=True),
    sa.Column('edu', sa.String(length=32), nullable=True),
    sa.Column('national', sa.String(length=16), nullable=True),
    sa.Column('birthday', sa.String(length=8), nullable=True),
    sa.Column('begin_date', sa.String(length=8), nullable=True),
    sa.Column('end_date', sa.String(length=8), nullable=True),
    sa.Column('resume', sa.Text(), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'ann_date', 'name')
    )
    op.create_index('idx_raw_stk_managers_ts_code', 'raw_tushare_stk_managers', ['ts_code'])
    op.create_index('idx_raw_stk_managers_ann_date', 'raw_tushare_stk_managers', ['ann_date'])

    # 4. raw_tushare_stk_rewards - 管理层薪酬和持股原始表
    op.create_table('raw_tushare_stk_rewards',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('ann_date', sa.String(length=8), nullable=False),
    sa.Column('end_date', sa.String(length=8), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('title', sa.String(length=64), nullable=True),
    sa.Column('reward', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('hold_vol', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'ann_date', 'end_date', 'name')
    )
    op.create_index('idx_raw_stk_rewards_ts_code', 'raw_tushare_stk_rewards', ['ts_code'])
    op.create_index('idx_raw_stk_rewards_end_date', 'raw_tushare_stk_rewards', ['end_date'])

    # 5. raw_tushare_new_share - IPO 新股列表原始表
    op.create_table('raw_tushare_new_share',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('sub_code', sa.String(length=16), nullable=True),
    sa.Column('name', sa.String(length=64), nullable=True),
    sa.Column('ipo_date', sa.String(length=8), nullable=True),
    sa.Column('issue_date', sa.String(length=8), nullable=True),
    sa.Column('amount', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('market_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('price', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('pe', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('limit_amount', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('funds', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('ballot', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code')
    )
    op.create_index('idx_raw_new_share_ipo_date', 'raw_tushare_new_share', ['ipo_date'])

    # 6. raw_tushare_daily_share - 每日股本变动原始表
    op.create_table('raw_tushare_daily_share',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    sa.Column('total_share', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('float_share', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('free_share', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('total_mv', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('circ_mv', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'trade_date')
    )
    op.create_index('idx_raw_daily_share_code_date', 'raw_tushare_daily_share', ['ts_code', 'trade_date'])
    op.create_index('idx_raw_daily_share_trade_date', 'raw_tushare_daily_share', ['trade_date'])

    # 7. raw_tushare_stk_list_his - 股票上市历史原始表
    op.create_table('raw_tushare_stk_list_his',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('list_date', sa.String(length=8), nullable=False),
    sa.Column('delist_date', sa.String(length=8), nullable=True),
    sa.Column('list_status', sa.String(length=1), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'list_date')
    )
    op.create_index('idx_raw_stk_list_his_ts_code', 'raw_tushare_stk_list_his', ['ts_code'])
    op.create_index('idx_raw_stk_list_his_list_date', 'raw_tushare_stk_list_his', ['list_date'])

    # =====================================================================
    # 11b. 行情补充（5 张）
    # =====================================================================

    # 8. raw_tushare_weekly - 周线行情原始表
    op.create_table('raw_tushare_weekly',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    sa.Column('open', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('high', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('low', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('close', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('pre_close', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('change', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('pct_chg', sa.Numeric(precision=10, scale=4), nullable=True),
    sa.Column('vol', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('amount', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'trade_date')
    )
    op.create_index('idx_raw_weekly_code_date', 'raw_tushare_weekly', ['ts_code', 'trade_date'])
    op.create_index('idx_raw_weekly_trade_date', 'raw_tushare_weekly', ['trade_date'])

    # 9. raw_tushare_monthly - 月线行情原始表
    op.create_table('raw_tushare_monthly',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    sa.Column('open', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('high', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('low', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('close', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('pre_close', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('change', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('pct_chg', sa.Numeric(precision=10, scale=4), nullable=True),
    sa.Column('vol', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('amount', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'trade_date')
    )
    op.create_index('idx_raw_monthly_code_date', 'raw_tushare_monthly', ['ts_code', 'trade_date'])
    op.create_index('idx_raw_monthly_trade_date', 'raw_tushare_monthly', ['trade_date'])

    # 10. raw_tushare_suspend_d - 停复牌信息原始表
    op.create_table('raw_tushare_suspend_d',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('suspend_date', sa.String(length=8), nullable=False),
    sa.Column('resume_date', sa.String(length=8), nullable=True),
    sa.Column('ann_date', sa.String(length=8), nullable=True),
    sa.Column('suspend_reason', sa.String(length=256), nullable=True),
    sa.Column('reason_type', sa.String(length=16), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'suspend_date')
    )
    op.create_index('idx_raw_suspend_d_ts_code', 'raw_tushare_suspend_d', ['ts_code'])
    op.create_index('idx_raw_suspend_d_suspend_date', 'raw_tushare_suspend_d', ['suspend_date'])

    # 11. raw_tushare_hsgt_top10 - 沪深港通十大成交股原始表
    op.create_table('raw_tushare_hsgt_top10',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    sa.Column('market_type', sa.String(length=8), nullable=False),
    sa.Column('rank', sa.Integer(), nullable=True),
    sa.Column('name', sa.String(length=64), nullable=True),
    sa.Column('close', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('change', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('net_amount', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('buy', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('sell', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'trade_date', 'market_type')
    )
    op.create_index('idx_raw_hsgt_top10_trade_date', 'raw_tushare_hsgt_top10', ['trade_date'])
    op.create_index('idx_raw_hsgt_top10_ts_code', 'raw_tushare_hsgt_top10', ['ts_code'])

    # 12. raw_tushare_ggt_daily - 港股通每日成交统计原始表
    op.create_table('raw_tushare_ggt_daily',
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    sa.Column('buy_amount', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('buy_volume', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('sell_amount', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('sell_volume', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('trade_date')
    )
    op.create_index('idx_raw_ggt_daily_trade_date', 'raw_tushare_ggt_daily', ['trade_date'])

    # =====================================================================
    # 11c. 市场参考数据（9 张）
    # =====================================================================

    # 13. raw_tushare_top10_holders - 前十大股东原始表
    op.create_table('raw_tushare_top10_holders',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('ann_date', sa.String(length=8), nullable=False),
    sa.Column('end_date', sa.String(length=8), nullable=False),
    sa.Column('holder_name', sa.String(length=128), nullable=False),
    sa.Column('hold_amount', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('hold_ratio', sa.Numeric(precision=10, scale=4), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'ann_date', 'end_date', 'holder_name')
    )
    op.create_index('idx_raw_top10_holders_ts_code', 'raw_tushare_top10_holders', ['ts_code'])
    op.create_index('idx_raw_top10_holders_end_date', 'raw_tushare_top10_holders', ['end_date'])

    # 14. raw_tushare_top10_floatholders - 前十大流通股东原始表
    op.create_table('raw_tushare_top10_floatholders',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('ann_date', sa.String(length=8), nullable=False),
    sa.Column('end_date', sa.String(length=8), nullable=False),
    sa.Column('holder_name', sa.String(length=128), nullable=False),
    sa.Column('hold_amount', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('hold_ratio', sa.Numeric(precision=10, scale=4), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'ann_date', 'end_date', 'holder_name')
    )
    op.create_index('idx_raw_top10_floatholders_ts_code', 'raw_tushare_top10_floatholders', ['ts_code'])
    op.create_index('idx_raw_top10_floatholders_end_date', 'raw_tushare_top10_floatholders', ['end_date'])

    # 15. raw_tushare_pledge_stat - 股权质押统计原始表
    op.create_table('raw_tushare_pledge_stat',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('end_date', sa.String(length=8), nullable=False),
    sa.Column('pledge_count', sa.Integer(), nullable=True),
    sa.Column('unrest_pledge', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('rest_pledge', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('total_share', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('pledge_ratio', sa.Numeric(precision=10, scale=4), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'end_date')
    )
    op.create_index('idx_raw_pledge_stat_ts_code', 'raw_tushare_pledge_stat', ['ts_code'])
    op.create_index('idx_raw_pledge_stat_end_date', 'raw_tushare_pledge_stat', ['end_date'])

    # 16. raw_tushare_pledge_detail - 股权质押明细原始表
    op.create_table('raw_tushare_pledge_detail',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('ann_date', sa.String(length=8), nullable=False),
    sa.Column('holder_name', sa.String(length=128), nullable=False),
    sa.Column('pledge_date', sa.String(length=8), nullable=False),
    sa.Column('pledge_amount', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('start_date', sa.String(length=8), nullable=True),
    sa.Column('end_date', sa.String(length=8), nullable=True),
    sa.Column('pledgor', sa.String(length=128), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'ann_date', 'holder_name', 'pledge_date')
    )
    op.create_index('idx_raw_pledge_detail_ts_code', 'raw_tushare_pledge_detail', ['ts_code'])
    op.create_index('idx_raw_pledge_detail_pledge_date', 'raw_tushare_pledge_detail', ['pledge_date'])

    # 17. raw_tushare_repurchase - 股票回购原始表
    op.create_table('raw_tushare_repurchase',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('ann_date', sa.String(length=8), nullable=False),
    sa.Column('end_date', sa.String(length=8), nullable=False),
    sa.Column('proc', sa.String(length=32), nullable=True),
    sa.Column('exp_date', sa.String(length=8), nullable=True),
    sa.Column('vol', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('amount', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('high_limit', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('low_limit', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'ann_date', 'end_date')
    )
    op.create_index('idx_raw_repurchase_ts_code', 'raw_tushare_repurchase', ['ts_code'])
    op.create_index('idx_raw_repurchase_ann_date', 'raw_tushare_repurchase', ['ann_date'])

    # 18. raw_tushare_share_float - 限售股解禁原始表
    op.create_table('raw_tushare_share_float',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('ann_date', sa.String(length=8), nullable=False),
    sa.Column('float_date', sa.String(length=8), nullable=False),
    sa.Column('float_share', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('float_ratio', sa.Numeric(precision=10, scale=4), nullable=True),
    sa.Column('holder_name', sa.String(length=128), nullable=True),
    sa.Column('share_type', sa.String(length=32), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'ann_date', 'float_date')
    )
    op.create_index('idx_raw_share_float_ts_code', 'raw_tushare_share_float', ['ts_code'])
    op.create_index('idx_raw_share_float_float_date', 'raw_tushare_share_float', ['float_date'])

    # 19. raw_tushare_block_trade - 大宗交易原始表
    op.create_table('raw_tushare_block_trade',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    sa.Column('price', sa.Numeric(precision=12, scale=4), nullable=False),
    sa.Column('vol', sa.Numeric(precision=20, scale=2), nullable=False),
    sa.Column('amount', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('buyer', sa.String(length=128), nullable=True),
    sa.Column('seller', sa.String(length=128), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'trade_date', 'price', 'vol')
    )
    op.create_index('idx_raw_block_trade_ts_code', 'raw_tushare_block_trade', ['ts_code'])
    op.create_index('idx_raw_block_trade_trade_date', 'raw_tushare_block_trade', ['trade_date'])

    # 20. raw_tushare_stk_holdernumber - 股东人数原始表
    op.create_table('raw_tushare_stk_holdernumber',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('ann_date', sa.String(length=8), nullable=False),
    sa.Column('end_date', sa.String(length=8), nullable=False),
    sa.Column('holder_num', sa.Integer(), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'ann_date', 'end_date')
    )
    op.create_index('idx_raw_stk_holdernumber_ts_code', 'raw_tushare_stk_holdernumber', ['ts_code'])
    op.create_index('idx_raw_stk_holdernumber_end_date', 'raw_tushare_stk_holdernumber', ['end_date'])

    # 21. raw_tushare_stk_holdertrade - 股东增减持原始表
    op.create_table('raw_tushare_stk_holdertrade',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('ann_date', sa.String(length=8), nullable=False),
    sa.Column('holder_name', sa.String(length=128), nullable=False),
    sa.Column('holder_type', sa.String(length=32), nullable=True),
    sa.Column('in_de', sa.String(length=8), nullable=True),
    sa.Column('change_vol', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('change_ratio', sa.Numeric(precision=10, scale=4), nullable=True),
    sa.Column('after_share', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('after_ratio', sa.Numeric(precision=10, scale=4), nullable=True),
    sa.Column('avg_price', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('total_share', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('begin_date', sa.String(length=8), nullable=True),
    sa.Column('close_date', sa.String(length=8), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'ann_date', 'holder_name')
    )
    op.create_index('idx_raw_stk_holdertrade_ts_code', 'raw_tushare_stk_holdertrade', ['ts_code'])
    op.create_index('idx_raw_stk_holdertrade_ann_date', 'raw_tushare_stk_holdertrade', ['ann_date'])

    # =====================================================================
    # 11d. 特色数据（9 张）
    # =====================================================================

    # 22. raw_tushare_report_rc - 券商月度金股原始表
    op.create_table('raw_tushare_report_rc',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('date', sa.String(length=8), nullable=False),
    sa.Column('broker', sa.String(length=64), nullable=False),
    sa.Column('title', sa.String(length=256), nullable=True),
    sa.Column('author', sa.String(length=64), nullable=True),
    sa.Column('report_date', sa.String(length=8), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'date', 'broker')
    )
    op.create_index('idx_raw_report_rc_ts_code', 'raw_tushare_report_rc', ['ts_code'])
    op.create_index('idx_raw_report_rc_date', 'raw_tushare_report_rc', ['date'])

    # 23. raw_tushare_cyq_perf - 筹码分布原始表
    op.create_table('raw_tushare_cyq_perf',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    sa.Column('his_low', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('his_high', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('cost_5pct', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('cost_15pct', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('cost_50pct', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('cost_85pct', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('cost_95pct', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('weight_avg', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('winner_rate', sa.Numeric(precision=10, scale=4), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'trade_date')
    )
    op.create_index('idx_raw_cyq_perf_ts_code', 'raw_tushare_cyq_perf', ['ts_code'])
    op.create_index('idx_raw_cyq_perf_trade_date', 'raw_tushare_cyq_perf', ['trade_date'])

    # 24. raw_tushare_cyq_chips - 筹码集中度原始表
    op.create_table('raw_tushare_cyq_chips',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    sa.Column('chip_ratio', sa.Numeric(precision=10, scale=4), nullable=True),
    sa.Column('chip_price', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('chip_vol', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'trade_date')
    )
    op.create_index('idx_raw_cyq_chips_ts_code', 'raw_tushare_cyq_chips', ['ts_code'])
    op.create_index('idx_raw_cyq_chips_trade_date', 'raw_tushare_cyq_chips', ['trade_date'])

    # 25. raw_tushare_stk_factor - 技术因子（日频）原始表
    op.create_table('raw_tushare_stk_factor',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    sa.Column('close', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('open', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('high', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('low', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('pre_close', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('change', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('pct_chg', sa.Numeric(precision=10, scale=4), nullable=True),
    sa.Column('vol', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('amount', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'trade_date')
    )
    op.create_index('idx_raw_stk_factor_ts_code', 'raw_tushare_stk_factor', ['ts_code'])
    op.create_index('idx_raw_stk_factor_trade_date', 'raw_tushare_stk_factor', ['trade_date'])

    # 26. raw_tushare_stk_factor_pro - 技术因子（日频增强版）原始表
    op.create_table('raw_tushare_stk_factor_pro',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    sa.Column('macd_dif', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('macd_dea', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('macd', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('kdj_k', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('kdj_d', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('kdj_j', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('rsi_6', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('rsi_12', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('rsi_24', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('boll_upper', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('boll_mid', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('boll_lower', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'trade_date')
    )
    op.create_index('idx_raw_stk_factor_pro_ts_code', 'raw_tushare_stk_factor_pro', ['ts_code'])
    op.create_index('idx_raw_stk_factor_pro_trade_date', 'raw_tushare_stk_factor_pro', ['trade_date'])

    # 27. raw_tushare_ccass_hold - 港股通持股汇总原始表
    op.create_table('raw_tushare_ccass_hold',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    sa.Column('hk_code', sa.String(length=16), nullable=True),
    sa.Column('name', sa.String(length=64), nullable=True),
    sa.Column('col_participant', sa.Integer(), nullable=True),
    sa.Column('col_holding', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('col_percent', sa.Numeric(precision=10, scale=4), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'trade_date')
    )
    op.create_index('idx_raw_ccass_hold_ts_code', 'raw_tushare_ccass_hold', ['ts_code'])
    op.create_index('idx_raw_ccass_hold_trade_date', 'raw_tushare_ccass_hold', ['trade_date'])

    # 28. raw_tushare_ccass_hold_detail - 港股通持股明细原始表
    op.create_table('raw_tushare_ccass_hold_detail',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    sa.Column('participant_id', sa.String(length=16), nullable=False),
    sa.Column('participant_name', sa.String(length=128), nullable=True),
    sa.Column('shareholding', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('shareholding_percent', sa.Numeric(precision=10, scale=4), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'trade_date', 'participant_id')
    )
    op.create_index('idx_raw_ccass_hold_detail_ts_code', 'raw_tushare_ccass_hold_detail', ['ts_code'])
    op.create_index('idx_raw_ccass_hold_detail_trade_date', 'raw_tushare_ccass_hold_detail', ['trade_date'])

    # 29. raw_tushare_hk_hold - 沪深港通持股明细原始表
    op.create_table('raw_tushare_hk_hold',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=True),
    sa.Column('vol', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('ratio', sa.Numeric(precision=10, scale=4), nullable=True),
    sa.Column('exchange', sa.String(length=8), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'trade_date')
    )
    op.create_index('idx_raw_hk_hold_ts_code', 'raw_tushare_hk_hold', ['ts_code'])
    op.create_index('idx_raw_hk_hold_trade_date', 'raw_tushare_hk_hold', ['trade_date'])

    # 30. raw_tushare_stk_surv - 股票调查问卷原始表
    op.create_table('raw_tushare_stk_surv',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('end_date', sa.String(length=8), nullable=False),
    sa.Column('survey_date', sa.String(length=8), nullable=False),
    sa.Column('survey_org', sa.String(length=128), nullable=True),
    sa.Column('survey_person', sa.String(length=64), nullable=True),
    sa.Column('survey_type', sa.String(length=32), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'end_date', 'survey_date')
    )
    op.create_index('idx_raw_stk_surv_ts_code', 'raw_tushare_stk_surv', ['ts_code'])
    op.create_index('idx_raw_stk_surv_end_date', 'raw_tushare_stk_surv', ['end_date'])

    # =====================================================================
    # 11e. 两融数据（4 张）
    # =====================================================================

    # 31. raw_tushare_margin - 融资融券交易汇总原始表
    op.create_table('raw_tushare_margin',
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    sa.Column('exchange_id', sa.String(length=8), nullable=False),
    sa.Column('rzye', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('rzmre', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('rzche', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('rqye', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('rqmcl', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('rqchl', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('rzrqye', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('trade_date', 'exchange_id')
    )
    op.create_index('idx_raw_margin_trade_date', 'raw_tushare_margin', ['trade_date'])

    # 32. raw_tushare_margin_detail - 融资融券交易明细原始表
    op.create_table('raw_tushare_margin_detail',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=True),
    sa.Column('rzye', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('rzmre', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('rzche', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('rqye', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('rqyl', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('rqmcl', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('rqchl', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('rzrqye', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'trade_date')
    )
    op.create_index('idx_raw_margin_detail_ts_code', 'raw_tushare_margin_detail', ['ts_code'])
    op.create_index('idx_raw_margin_detail_trade_date', 'raw_tushare_margin_detail', ['trade_date'])

    # 33. raw_tushare_margin_target - 融资融券标的原始表
    op.create_table('raw_tushare_margin_target',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=True),
    sa.Column('in_date', sa.String(length=8), nullable=True),
    sa.Column('out_date', sa.String(length=8), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code')
    )
    op.create_index('idx_raw_margin_target_ts_code', 'raw_tushare_margin_target', ['ts_code'])

    # 34. raw_tushare_slb_len - 转融通借入原始表
    op.create_table('raw_tushare_slb_len',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=True),
    sa.Column('slb_amt', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('slb_vol', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('slb_ratio', sa.Numeric(precision=10, scale=4), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'trade_date')
    )
    op.create_index('idx_raw_slb_len_ts_code', 'raw_tushare_slb_len', ['ts_code'])
    op.create_index('idx_raw_slb_len_trade_date', 'raw_tushare_slb_len', ['trade_date'])

    # =====================================================================
    # 11f. 打板专题（14 张）
    # =====================================================================

    # 35. raw_tushare_limit_list_d - 每日涨跌停统计原始表
    op.create_table('raw_tushare_limit_list_d',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=True),
    sa.Column('close', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('pct_chg', sa.Numeric(precision=10, scale=4), nullable=True),
    sa.Column('amp', sa.Numeric(precision=10, scale=4), nullable=True),
    sa.Column('fc_ratio', sa.Numeric(precision=10, scale=4), nullable=True),
    sa.Column('fl_ratio', sa.Numeric(precision=10, scale=4), nullable=True),
    sa.Column('fd_amount', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('first_time', sa.String(length=8), nullable=True),
    sa.Column('last_time', sa.String(length=8), nullable=True),
    sa.Column('open_times', sa.Integer(), nullable=True),
    sa.Column('up_stat', sa.String(length=4), nullable=True),
    sa.Column('limit_times', sa.Integer(), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'trade_date')
    )
    op.create_index('idx_raw_limit_list_d_ts_code', 'raw_tushare_limit_list_d', ['ts_code'])
    op.create_index('idx_raw_limit_list_d_trade_date', 'raw_tushare_limit_list_d', ['trade_date'])

    # 36. raw_tushare_ths_limit - 同花顺涨跌停原始表
    op.create_table('raw_tushare_ths_limit',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=True),
    sa.Column('close', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('pct_chg', sa.Numeric(precision=10, scale=4), nullable=True),
    sa.Column('limit_type', sa.String(length=4), nullable=True),
    sa.Column('first_time', sa.String(length=8), nullable=True),
    sa.Column('last_time', sa.String(length=8), nullable=True),
    sa.Column('open_times', sa.Integer(), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'trade_date')
    )
    op.create_index('idx_raw_ths_limit_ts_code', 'raw_tushare_ths_limit', ['ts_code'])
    op.create_index('idx_raw_ths_limit_trade_date', 'raw_tushare_ths_limit', ['trade_date'])

    # 37. raw_tushare_limit_step - 涨跌停阶梯原始表
    op.create_table('raw_tushare_limit_step',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=True),
    sa.Column('close', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('pct_chg', sa.Numeric(precision=10, scale=4), nullable=True),
    sa.Column('step', sa.Integer(), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'trade_date')
    )
    op.create_index('idx_raw_limit_step_ts_code', 'raw_tushare_limit_step', ['ts_code'])
    op.create_index('idx_raw_limit_step_trade_date', 'raw_tushare_limit_step', ['trade_date'])

    # 38. raw_tushare_hm_board - 热门板块原始表
    op.create_table('raw_tushare_hm_board',
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    sa.Column('board_code', sa.String(length=16), nullable=False),
    sa.Column('board_name', sa.String(length=64), nullable=True),
    sa.Column('pct_chg', sa.Numeric(precision=10, scale=4), nullable=True),
    sa.Column('rank', sa.Integer(), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('trade_date', 'board_code')
    )
    op.create_index('idx_raw_hm_board_trade_date', 'raw_tushare_hm_board', ['trade_date'])

    # 39. raw_tushare_hm_list - 热门股票原始表
    op.create_table('raw_tushare_hm_list',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=True),
    sa.Column('close', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('pct_chg', sa.Numeric(precision=10, scale=4), nullable=True),
    sa.Column('rank', sa.Integer(), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'trade_date')
    )
    op.create_index('idx_raw_hm_list_ts_code', 'raw_tushare_hm_list', ['ts_code'])
    op.create_index('idx_raw_hm_list_trade_date', 'raw_tushare_hm_list', ['trade_date'])

    # 40. raw_tushare_hm_detail - 热门股票明细原始表
    op.create_table('raw_tushare_hm_detail',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=True),
    sa.Column('close', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('pct_chg', sa.Numeric(precision=10, scale=4), nullable=True),
    sa.Column('reason', sa.String(length=256), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'trade_date')
    )
    op.create_index('idx_raw_hm_detail_ts_code', 'raw_tushare_hm_detail', ['ts_code'])
    op.create_index('idx_raw_hm_detail_trade_date', 'raw_tushare_hm_detail', ['trade_date'])

    # 41. raw_tushare_stk_auction - 集合竞价原始表
    op.create_table('raw_tushare_stk_auction',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=True),
    sa.Column('open', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('pre_close', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('pct_chg', sa.Numeric(precision=10, scale=4), nullable=True),
    sa.Column('vol', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('amount', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'trade_date')
    )
    op.create_index('idx_raw_stk_auction_ts_code', 'raw_tushare_stk_auction', ['ts_code'])
    op.create_index('idx_raw_stk_auction_trade_date', 'raw_tushare_stk_auction', ['trade_date'])

    # 42. raw_tushare_stk_auction_o - 集合竞价（开盘）原始表
    op.create_table('raw_tushare_stk_auction_o',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=True),
    sa.Column('open', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('pre_close', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('pct_chg', sa.Numeric(precision=10, scale=4), nullable=True),
    sa.Column('vol', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('amount', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'trade_date')
    )
    op.create_index('idx_raw_stk_auction_o_ts_code', 'raw_tushare_stk_auction_o', ['ts_code'])
    op.create_index('idx_raw_stk_auction_o_trade_date', 'raw_tushare_stk_auction_o', ['trade_date'])

    # 43. raw_tushare_kpl_list - 科创板涨跌停原始表
    op.create_table('raw_tushare_kpl_list',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=True),
    sa.Column('close', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('pct_chg', sa.Numeric(precision=10, scale=4), nullable=True),
    sa.Column('limit_type', sa.String(length=4), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'trade_date')
    )
    op.create_index('idx_raw_kpl_list_ts_code', 'raw_tushare_kpl_list', ['ts_code'])
    op.create_index('idx_raw_kpl_list_trade_date', 'raw_tushare_kpl_list', ['trade_date'])

    # 44. raw_tushare_kpl_concept - 科创板概念原始表
    op.create_table('raw_tushare_kpl_concept',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    sa.Column('concept_code', sa.String(length=16), nullable=False),
    sa.Column('concept_name', sa.String(length=64), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'trade_date', 'concept_code')
    )
    op.create_index('idx_raw_kpl_concept_ts_code', 'raw_tushare_kpl_concept', ['ts_code'])
    op.create_index('idx_raw_kpl_concept_trade_date', 'raw_tushare_kpl_concept', ['trade_date'])

    # 45. raw_tushare_broker_recommend - 券商推荐原始表
    op.create_table('raw_tushare_broker_recommend',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('date', sa.String(length=8), nullable=False),
    sa.Column('broker', sa.String(length=64), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=True),
    sa.Column('rating', sa.String(length=16), nullable=True),
    sa.Column('target_price', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'date', 'broker')
    )
    op.create_index('idx_raw_broker_recommend_ts_code', 'raw_tushare_broker_recommend', ['ts_code'])
    op.create_index('idx_raw_broker_recommend_date', 'raw_tushare_broker_recommend', ['date'])

    # 46. raw_tushare_ths_hot - 同花顺热榜原始表
    op.create_table('raw_tushare_ths_hot',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=True),
    sa.Column('close', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('pct_chg', sa.Numeric(precision=10, scale=4), nullable=True),
    sa.Column('hot_rank', sa.Integer(), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'trade_date')
    )
    op.create_index('idx_raw_ths_hot_ts_code', 'raw_tushare_ths_hot', ['ts_code'])
    op.create_index('idx_raw_ths_hot_trade_date', 'raw_tushare_ths_hot', ['trade_date'])

    # 47. raw_tushare_dc_hot - 东财热榜原始表
    op.create_table('raw_tushare_dc_hot',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('trade_date', sa.String(length=8), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=True),
    sa.Column('close', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('pct_chg', sa.Numeric(precision=10, scale=4), nullable=True),
    sa.Column('hot_rank', sa.Integer(), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'trade_date')
    )
    op.create_index('idx_raw_dc_hot_ts_code', 'raw_tushare_dc_hot', ['ts_code'])
    op.create_index('idx_raw_dc_hot_trade_date', 'raw_tushare_dc_hot', ['trade_date'])

    # 48. raw_tushare_ggt_monthly - 港股通月度统计原始表
    op.create_table('raw_tushare_ggt_monthly',
    sa.Column('month', sa.String(length=8), nullable=False),
    sa.Column('day_buy_amt', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('day_buy_vol', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('day_sell_amt', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('day_sell_vol', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('total_buy_amt', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('total_buy_vol', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('total_sell_amt', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('total_sell_vol', sa.Numeric(precision=20, scale=2), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('month')
    )
    op.create_index('idx_raw_ggt_monthly_month', 'raw_tushare_ggt_monthly', ['month'])



def downgrade() -> None:
    """Downgrade schema."""
    # 按相反顺序删除所有表（从 48 到 1）

    # 11f. 打板专题（14 张）
    op.drop_table('raw_tushare_ggt_monthly')
    op.drop_table('raw_tushare_dc_hot')
    op.drop_table('raw_tushare_ths_hot')
    op.drop_table('raw_tushare_broker_recommend')
    op.drop_table('raw_tushare_kpl_concept')
    op.drop_table('raw_tushare_kpl_list')
    op.drop_table('raw_tushare_stk_auction_o')
    op.drop_table('raw_tushare_stk_auction')
    op.drop_table('raw_tushare_hm_detail')
    op.drop_table('raw_tushare_hm_list')
    op.drop_table('raw_tushare_hm_board')
    op.drop_table('raw_tushare_limit_step')
    op.drop_table('raw_tushare_ths_limit')
    op.drop_table('raw_tushare_limit_list_d')

    # 11e. 两融数据（4 张）
    op.drop_table('raw_tushare_slb_len')
    op.drop_table('raw_tushare_margin_target')
    op.drop_table('raw_tushare_margin_detail')
    op.drop_table('raw_tushare_margin')

    # 11d. 特色数据（9 张）
    op.drop_table('raw_tushare_stk_surv')
    op.drop_table('raw_tushare_hk_hold')
    op.drop_table('raw_tushare_ccass_hold_detail')
    op.drop_table('raw_tushare_ccass_hold')
    op.drop_table('raw_tushare_stk_factor_pro')
    op.drop_table('raw_tushare_stk_factor')
    op.drop_table('raw_tushare_cyq_chips')
    op.drop_table('raw_tushare_cyq_perf')
    op.drop_table('raw_tushare_report_rc')

    # 11c. 市场参考数据（9 张）
    op.drop_table('raw_tushare_stk_holdertrade')
    op.drop_table('raw_tushare_stk_holdernumber')
    op.drop_table('raw_tushare_block_trade')
    op.drop_table('raw_tushare_share_float')
    op.drop_table('raw_tushare_repurchase')
    op.drop_table('raw_tushare_pledge_detail')
    op.drop_table('raw_tushare_pledge_stat')
    op.drop_table('raw_tushare_top10_floatholders')
    op.drop_table('raw_tushare_top10_holders')

    # 11b. 行情补充（5 张）
    op.drop_table('raw_tushare_ggt_daily')
    op.drop_table('raw_tushare_hsgt_top10')
    op.drop_table('raw_tushare_suspend_d')
    op.drop_table('raw_tushare_monthly')
    op.drop_table('raw_tushare_weekly')

    # 11a. 基础数据补充（7 张）
    op.drop_table('raw_tushare_stk_list_his')
    op.drop_table('raw_tushare_daily_share')
    op.drop_table('raw_tushare_new_share')
    op.drop_table('raw_tushare_stk_rewards')
    op.drop_table('raw_tushare_stk_managers')
    op.drop_table('raw_tushare_stock_company')
    op.drop_table('raw_tushare_namechange')
