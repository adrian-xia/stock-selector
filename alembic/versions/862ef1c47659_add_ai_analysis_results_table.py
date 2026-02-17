"""add ai_analysis_results table

Revision ID: 862ef1c47659
Revises: 5bd9bf8c67e8
Create Date: 2026-02-17 23:26:28.646759

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '862ef1c47659'
down_revision: Union[str, Sequence[str], None] = '5bd9bf8c67e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('ai_analysis_results',
    sa.Column('ts_code', sa.String(length=20), nullable=False, comment='股票代码'),
    sa.Column('trade_date', sa.Date(), nullable=False, comment='分析日期'),
    sa.Column('ai_score', sa.Integer(), nullable=False, comment='AI 评分 1-100'),
    sa.Column('ai_signal', sa.String(length=20), nullable=False, comment='信号：STRONG_BUY/BUY/HOLD/SELL/STRONG_SELL'),
    sa.Column('ai_summary', sa.Text(), nullable=False, comment='分析摘要'),
    sa.Column('prompt_version', sa.String(length=20), nullable=False, comment='Prompt 模板版本'),
    sa.Column('token_usage', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='Token 用量 {prompt_tokens, completion_tokens, total_tokens}'),
    sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
    sa.PrimaryKeyConstraint('ts_code', 'trade_date'),
    comment='AI 分析结果'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('ai_analysis_results')
