"""add_dragon_tiger_unique_constraint

Revision ID: 6c239fe672ab
Revises: 5b8b60fff8da
Create Date: 2026-02-17 02:30:48.167693

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6c239fe672ab'
down_revision: Union[str, Sequence[str], None] = '5b8b60fff8da'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """为 dragon_tiger 表添加唯一约束，支持 UPSERT 写入。"""
    op.create_unique_constraint(
        "uq_dragon_tiger_code_date_reason",
        "dragon_tiger",
        ["ts_code", "trade_date", "reason"],
    )


def downgrade() -> None:
    """移除 dragon_tiger 唯一约束。"""
    op.drop_constraint(
        "uq_dragon_tiger_code_date_reason",
        "dragon_tiger",
        type_="unique",
    )
