"""add_v2_columns_to_strategies

Revision ID: 293b80375079
Revises: 2eaeb04efa46
Create Date: 2026-03-07 00:35:44.283356

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '293b80375079'
down_revision: Union[str, Sequence[str], None] = '2eaeb04efa46'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 新增 V2 策略引擎字段
    op.add_column('strategies', sa.Column('role', sa.String(20), nullable=True, server_default='trigger'))
    op.add_column('strategies', sa.Column('signal_group', sa.String(20), nullable=True))
    op.add_column('strategies', sa.Column('ai_rating', sa.Numeric(4, 2), nullable=True, server_default='5.0'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('strategies', 'ai_rating')
    op.drop_column('strategies', 'signal_group')
    op.drop_column('strategies', 'role')
