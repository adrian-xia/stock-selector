"""add starmap tables: macro_signal_daily, sector_resonance_daily, trade_plan_daily_ext

Revision ID: i3c4d5e6f7g8
Revises: h2b3c4d5e6f7
Create Date: 2026-03-05
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "i3c4d5e6f7g8"
down_revision = "h2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- macro_signal_daily ---
    op.create_table(
        "macro_signal_daily",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("trade_date", sa.Date, nullable=False, unique=True),
        sa.Column("risk_appetite", sa.String(8), nullable=False),
        sa.Column("global_risk_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("positive_sectors", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("negative_sectors", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("macro_summary", sa.Text, nullable=False),
        sa.Column("key_drivers", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("raw_payload", postgresql.JSONB, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("model_name", sa.String(128), nullable=False),
        sa.Column("prompt_version", sa.String(32), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_macro_signal_trade_date", "macro_signal_daily", [sa.text("trade_date DESC")])
    op.create_index("idx_macro_signal_hash", "macro_signal_daily", ["content_hash"])

    # --- sector_resonance_daily ---
    op.create_table(
        "sector_resonance_daily",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("sector_code", sa.String(32), nullable=False),
        sa.Column("sector_name", sa.String(64), nullable=False),
        sa.Column("news_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("moneyflow_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("trend_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("final_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 2), nullable=False),
        sa.Column("drivers", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("trade_date", "sector_code", name="uq_sector_resonance"),
    )
    op.create_index(
        "idx_sector_resonance_trade_date_score",
        "sector_resonance_daily",
        [sa.text("trade_date DESC"), sa.text("final_score DESC")],
    )

    # --- trade_plan_daily_ext ---
    op.create_table(
        "trade_plan_daily_ext",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("ts_code", sa.String(20), nullable=False),
        sa.Column("source_strategy", sa.String(64), nullable=False),
        sa.Column("plan_type", sa.String(32), nullable=False),
        sa.Column("plan_status", sa.String(16), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("entry_rule", sa.Text, nullable=False),
        sa.Column("stop_loss_rule", sa.Text, nullable=False),
        sa.Column("take_profit_rule", sa.Text, nullable=False),
        sa.Column("emergency_exit_text", sa.Text, nullable=True),
        sa.Column("emergency_exit_config", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("position_suggestion", sa.Numeric(5, 2), nullable=False),
        sa.Column("market_regime", sa.String(16), nullable=False),
        sa.Column("market_risk_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("sector_name", sa.String(64), nullable=True),
        sa.Column("sector_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("confidence", sa.Numeric(5, 2), nullable=False),
        sa.Column("reasoning", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("risk_flags", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("trade_date", "ts_code", "source_strategy", name="uq_trade_plan_ext"),
    )
    op.create_index("idx_trade_plan_ext_trade_date", "trade_plan_daily_ext", [sa.text("trade_date DESC")])
    op.create_index(
        "idx_trade_plan_ext_status",
        "trade_plan_daily_ext",
        [sa.text("trade_date DESC"), "plan_status"],
    )


def downgrade() -> None:
    op.drop_table("trade_plan_daily_ext")
    op.drop_table("sector_resonance_daily")
    op.drop_table("macro_signal_daily")
