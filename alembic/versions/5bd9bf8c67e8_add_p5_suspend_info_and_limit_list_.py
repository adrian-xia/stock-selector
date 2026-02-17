"""add p5 suspend_info and limit_list_daily business tables

Revision ID: 5bd9bf8c67e8
Revises: 6c239fe672ab
Create Date: 2026-02-17 21:49:15.416490

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5bd9bf8c67e8'
down_revision: Union[str, Sequence[str], None] = '6c239fe672ab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. suspend_info — 停复牌信息业务表
    op.create_table(
        'suspend_info',
        sa.Column('ts_code', sa.String(length=16), nullable=False),
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('suspend_timing', sa.String(length=8), nullable=True),
        sa.Column('suspend_type', sa.String(length=16), nullable=True),
        sa.Column('suspend_reason', sa.String(length=256), nullable=True),
        sa.Column('resume_date', sa.Date(), nullable=True),
        sa.Column('data_source', sa.String(length=16), server_default='tushare', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('ts_code', 'trade_date'),
    )
    op.create_index('idx_suspend_info_ts_code', 'suspend_info', ['ts_code'])
    op.create_index('idx_suspend_info_trade_date', 'suspend_info', ['trade_date'])

    # 2. limit_list_daily — 每日涨跌停统计业务表
    op.create_table(
        'limit_list_daily',
        sa.Column('ts_code', sa.String(length=16), nullable=False),
        sa.Column('trade_date', sa.Date(), nullable=False),
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
        sa.Column('data_source', sa.String(length=16), server_default='tushare', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('ts_code', 'trade_date'),
    )
    op.create_index(
        'idx_limit_list_daily_code_date', 'limit_list_daily',
        ['ts_code', sa.text('trade_date DESC')],
    )
    op.create_index('idx_limit_list_daily_trade_date', 'limit_list_daily', ['trade_date'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('limit_list_daily')
    op.drop_table('suspend_info')
