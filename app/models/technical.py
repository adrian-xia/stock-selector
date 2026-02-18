from datetime import date, datetime

from sqlalchemy import Date, DateTime, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TechnicalDaily(Base):
    __tablename__ = "technical_daily"
    __table_args__ = (
        Index("idx_technical_code_date", "ts_code", "trade_date", postgresql_ops={"trade_date": "DESC"}),
        Index("idx_technical_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)

    # Moving averages
    ma5: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    ma10: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    ma20: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    ma60: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    ma120: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    ma250: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    # MACD
    macd_dif: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    macd_dea: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    macd_hist: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)

    # KDJ
    kdj_k: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    kdj_d: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    kdj_j: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)

    # RSI
    rsi6: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    rsi12: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    rsi24: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)

    # Bollinger Bands
    boll_upper: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    boll_mid: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    boll_lower: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    # Volume indicators
    vol_ma5: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    vol_ma10: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    vol_ratio: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)

    # Other
    atr14: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)

    # Extended indicators (V2 策略扩展)
    wr: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)  # Williams %R (14)
    cci: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)  # CCI (14)
    bias: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)  # BIAS (基于 MA20)
    obv: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)  # OBV 能量潮
    donchian_upper: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)  # 唐奇安上轨 (20)
    donchian_lower: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)  # 唐奇安下轨 (20)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
