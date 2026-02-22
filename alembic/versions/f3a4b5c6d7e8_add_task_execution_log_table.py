"""新增 task_execution_log 任务执行日志表

记录调度任务的执行历史，支持回溯排查。

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-02-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "f3a4b5c6d7e8"
down_revision = "e2f3a4b5c6d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "task_execution_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("task_name", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("duration_seconds", sa.Numeric(10, 2), nullable=True),
        sa.Column("result_summary", JSONB, nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("trade_date", sa.Date(), nullable=True),
    )

    op.create_index(
        "idx_task_log_name_started",
        "task_execution_log",
        ["task_name", sa.text("started_at DESC")],
    )
    op.create_index(
        "idx_task_log_status",
        "task_execution_log",
        ["status"],
    )
    op.create_index(
        "idx_task_log_trade_date",
        "task_execution_log",
        ["trade_date"],
    )


def downgrade() -> None:
    op.drop_index("idx_task_log_trade_date", table_name="task_execution_log")
    op.drop_index("idx_task_log_status", table_name="task_execution_log")
    op.drop_index("idx_task_log_name_started", table_name="task_execution_log")
    op.drop_table("task_execution_log")
