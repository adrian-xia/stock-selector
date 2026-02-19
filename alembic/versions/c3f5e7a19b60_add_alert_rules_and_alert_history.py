"""add alert_rules and alert_history tables

Revision ID: c3f5e7a19b60
Revises: b2e4d9f13a58
Create Date: 2026-02-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "c3f5e7a19b60"
down_revision = "b2e4d9f13a58"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alert_rules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("rule_type", sa.String(30), nullable=False),
        sa.Column("params", JSONB(), nullable=False, server_default="{}"),
        sa.Column("enabled", sa.Boolean(), server_default="true"),
        sa.Column("cooldown_minutes", sa.Integer(), server_default="30"),
        sa.Column("last_triggered_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alert_rules_ts_code", "alert_rules", ["ts_code"])
    op.create_index("ix_alert_rules_enabled", "alert_rules", ["enabled"])

    op.create_table(
        "alert_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("rule_id", sa.Integer(), nullable=False),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("rule_type", sa.String(30), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("notified", sa.Boolean(), server_default="false"),
        sa.Column("triggered_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alert_history_ts_code", "alert_history", ["ts_code"])
    op.create_index("ix_alert_history_triggered_at", "alert_history", ["triggered_at"])


def downgrade() -> None:
    op.drop_table("alert_history")
    op.drop_table("alert_rules")
