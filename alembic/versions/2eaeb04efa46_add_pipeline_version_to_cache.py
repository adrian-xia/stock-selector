"""add_pipeline_version_to_cache

Revision ID: 2eaeb04efa46
Revises: c2d4b1241fc4
Create Date: 2026-03-07 00:31:34.165353

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2eaeb04efa46'
down_revision: Union[str, Sequence[str], None] = 'c2d4b1241fc4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 新增 pipeline_version 列，默认值为 1（V1 缓存）
    op.add_column('pipeline_cache', sa.Column('pipeline_version', sa.Integer(), nullable=False, server_default='1'))

    # 清除所有 V1 缓存，避免 Layer 语义错乱
    op.execute("DELETE FROM pipeline_cache WHERE pipeline_version = 1")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('pipeline_cache', 'pipeline_version')
