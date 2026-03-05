"""StarMap 数据库模型：宏观信号、行业共振、交易计划扩展。"""

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, Index, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MacroSignalDaily(Base):
    """每日宏观结构化信号表（LLM 提取结果）。

    存储经 LLM 提取的宏观信号：风险偏好、利好/利空行业、摘要等。
    以 trade_date 为幂等键，UPSERT 更新。
    """

    __tablename__ = "macro_signal_daily"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    risk_appetite: Mapped[str] = mapped_column(String(8), nullable=False)  # high/mid/low
    global_risk_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)  # 0~100
    positive_sectors: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="'[]'::jsonb")
    negative_sectors: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="'[]'::jsonb")
    macro_summary: Mapped[str] = mapped_column(Text, nullable=False)
    key_drivers: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="'[]'::jsonb")
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # 输入新闻内容哈希
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_macro_signal_trade_date", trade_date.desc()),
        Index("idx_macro_signal_hash", "content_hash"),
    )


class SectorResonanceDaily(Base):
    """每日行业共振评分表。

    存储行业共振评分：新闻分、资金分、趋势分及加权总分。
    以 (trade_date, sector_code) 为幂等键。
    """

    __tablename__ = "sector_resonance_daily"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    sector_code: Mapped[str] = mapped_column(String(32), nullable=False)
    sector_name: Mapped[str] = mapped_column(String(64), nullable=False)
    news_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    moneyflow_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    trend_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    final_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    drivers: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="'[]'::jsonb")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("trade_date", "sector_code", name="uq_sector_resonance"),
        Index("idx_sector_resonance_trade_date_score", trade_date.desc(), final_score.desc()),
    )


class TradePlanDailyExt(Base):
    """交易计划扩展表（StarMap 生成）。

    记录增强交易计划：入场/止损/止盈规则、仓位建议、风控信息等。
    以 (trade_date, ts_code, source_strategy) 为幂等键。
    """

    __tablename__ = "trade_plan_daily_ext"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    ts_code: Mapped[str] = mapped_column(String(20), nullable=False)
    source_strategy: Mapped[str] = mapped_column(String(64), nullable=False)
    plan_type: Mapped[str] = mapped_column(String(32), nullable=False)  # breakout/pullback/reversal
    plan_status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="'PENDING'"
    )  # PENDING/EXPIRED
    entry_rule: Mapped[str] = mapped_column(Text, nullable=False)
    stop_loss_rule: Mapped[str] = mapped_column(Text, nullable=False)
    take_profit_rule: Mapped[str] = mapped_column(Text, nullable=False)
    emergency_exit_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    emergency_exit_config: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="'{}'::jsonb"
    )
    position_suggestion: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    market_regime: Mapped[str] = mapped_column(String(16), nullable=False)
    market_risk_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    sector_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sector_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    confidence: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    reasoning: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="'[]'::jsonb")
    risk_flags: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="'[]'::jsonb")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "trade_date", "ts_code", "source_strategy", name="uq_trade_plan_ext"
        ),
        Index("idx_trade_plan_ext_trade_date", trade_date.desc()),
        Index("idx_trade_plan_ext_status", trade_date.desc(), "plan_status"),
    )
