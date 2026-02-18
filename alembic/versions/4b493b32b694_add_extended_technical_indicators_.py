"""add_extended_technical_indicators_columns

Revision ID: 4b493b32b694
Revises: 862ef1c47659
Create Date: 2026-02-18 20:22:05.237300

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '4b493b32b694'
down_revision: Union[str, Sequence[str], None] = '862ef1c47659'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """为 technical_daily / index_technical_daily / concept_technical_daily 新增扩展指标列。"""
    # technical_daily: 新增 6 个扩展指标列
    for table in ("technical_daily", "index_technical_daily", "concept_technical_daily"):
        op.add_column(table, sa.Column('wr', sa.Numeric(precision=10, scale=4), nullable=True))
        op.add_column(table, sa.Column('cci', sa.Numeric(precision=10, scale=4), nullable=True))
        op.add_column(table, sa.Column('bias', sa.Numeric(precision=10, scale=4), nullable=True))
        op.add_column(table, sa.Column('obv', sa.Numeric(precision=20, scale=2), nullable=True))
        op.add_column(table, sa.Column('donchian_upper', sa.Numeric(precision=10, scale=2), nullable=True))
        op.add_column(table, sa.Column('donchian_lower', sa.Numeric(precision=10, scale=2), nullable=True))


def downgrade() -> None:
    """移除扩展指标列。"""
    for table in ("technical_daily", "index_technical_daily", "concept_technical_daily"):
        op.drop_column(table, 'donchian_lower')
        op.drop_column(table, 'donchian_upper')
        op.drop_column(table, 'obv')
        op.drop_column(table, 'bias')
        op.drop_column(table, 'cci')
        op.drop_column(table, 'wr')
