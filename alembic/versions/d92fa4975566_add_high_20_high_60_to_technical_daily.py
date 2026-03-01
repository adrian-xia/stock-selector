"""add high_20 high_60 to technical_daily

Revision ID: d92fa4975566
Revises: h2b3c4d5e6f7
Create Date: 2026-03-02 00:18:03.867544

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd92fa4975566'
down_revision: Union[str, Sequence[str], None] = 'h2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """新增 high_20、high_60 列到 technical_daily 表。"""
    op.add_column('technical_daily', sa.Column('high_20', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('technical_daily', sa.Column('high_60', sa.Numeric(precision=10, scale=2), nullable=True))


def downgrade() -> None:
    """回滚：移除 high_20、high_60 列。"""
    op.drop_column('technical_daily', 'high_60')
    op.drop_column('technical_daily', 'high_20')
