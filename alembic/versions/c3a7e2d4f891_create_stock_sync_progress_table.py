"""create stock_sync_progress table

Revision ID: c3a7e2d4f891
Revises: b8c91b1f1c27
Create Date: 2026-02-13 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c3a7e2d4f891'
down_revision: Union[str, Sequence[str], None] = 'b8c91b1f1c27'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建 stock_sync_progress 表（累积进度模型）。"""
    op.create_table(
        'stock_sync_progress',
        sa.Column('ts_code', sa.String(16), primary_key=True),
        sa.Column('data_date', sa.Date(), nullable=False, server_default='1900-01-01'),
        sa.Column('indicator_date', sa.Date(), nullable=False, server_default='1900-01-01'),
        sa.Column('status', sa.String(16), nullable=False, server_default='idle'),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )


def downgrade() -> None:
    """删除 stock_sync_progress 表。"""
    op.drop_table('stock_sync_progress')
