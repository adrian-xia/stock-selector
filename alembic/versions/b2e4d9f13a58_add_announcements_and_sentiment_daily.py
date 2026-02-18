"""add announcements and sentiment_daily tables

Revision ID: b2e4d9f13a58
Revises: a1f3c8d92e47
Create Date: 2026-02-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "b2e4d9f13a58"
down_revision = "a1f3c8d92e47"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "announcements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ts_code", sa.String(16), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("pub_date", sa.Date(), nullable=False),
        sa.Column("url", sa.String(512), nullable=True),
        sa.Column("sentiment_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("sentiment_label", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ts_code", "source", "title", "pub_date", name="uq_announcement"),
    )
    op.create_index("ix_announcements_ts_code", "announcements", ["ts_code"])
    op.create_index("ix_announcements_pub_date", "announcements", ["pub_date"])

    op.create_table(
        "sentiment_daily",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ts_code", sa.String(16), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("avg_sentiment", sa.Numeric(5, 4), nullable=True),
        sa.Column("news_count", sa.Integer(), server_default="0"),
        sa.Column("positive_count", sa.Integer(), server_default="0"),
        sa.Column("negative_count", sa.Integer(), server_default="0"),
        sa.Column("neutral_count", sa.Integer(), server_default="0"),
        sa.Column("source_breakdown", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ts_code", "trade_date", name="uq_sentiment_daily"),
    )
    op.create_index("ix_sentiment_daily_ts_code", "sentiment_daily", ["ts_code"])
    op.create_index("ix_sentiment_daily_trade_date", "sentiment_daily", ["trade_date"])


def downgrade() -> None:
    op.drop_index("ix_sentiment_daily_trade_date", table_name="sentiment_daily")
    op.drop_index("ix_sentiment_daily_ts_code", table_name="sentiment_daily")
    op.drop_table("sentiment_daily")
    op.drop_index("ix_announcements_pub_date", table_name="announcements")
    op.drop_index("ix_announcements_ts_code", table_name="announcements")
    op.drop_table("announcements")
