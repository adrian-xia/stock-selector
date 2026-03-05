"""merge_starmap_tables

Revision ID: c2d4b1241fc4
Revises: d92fa4975566, i3c4d5e6f7g8
Create Date: 2026-03-05 23:10:02.952322

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2d4b1241fc4'
down_revision: Union[str, Sequence[str], None] = ('d92fa4975566', 'i3c4d5e6f7g8')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
