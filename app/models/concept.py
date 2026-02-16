"""板块数据模型。

包含板块基础信息、日线行情、成分股、技术指标等业务表。
统一三个数据源（同花顺、东方财富、通达信）到 concept_* 业务表。
"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ConceptIndex(Base):
    """板块基础信息表。"""

    __tablename__ = "concept_index"

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    src: Mapped[str] = mapped_column(String(16))  # THS/DC/TDX
    type: Mapped[str | None] = mapped_column(String(16), nullable=True)  # 板块类型
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class ConceptDaily(Base):
    """板块日线行情表。"""

    __tablename__ = "concept_daily"
    __table_args__ = (
        Index(
            "idx_concept_daily_code_date",
            "ts_code",
            "trade_date",
            postgresql_ops={"trade_date": "DESC"},
        ),
        Index("idx_concept_daily_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    open: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    high: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    low: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    close: Mapped[float] = mapped_column(Numeric(12, 4))
    pre_close: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    change: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    pct_chg: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    vol: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    amount: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class ConceptMember(Base):
    """板块成分股表。"""

    __tablename__ = "concept_member"
    __table_args__ = (
        Index("idx_concept_member_concept_code", "concept_code"),
        Index("idx_concept_member_stock_code", "stock_code"),
        Index("idx_concept_member_in_date", "in_date"),
    )

    concept_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    stock_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    in_date: Mapped[date] = mapped_column(Date, primary_key=True)
    out_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class ConceptTechnicalDaily(Base):
    """板块技术指标表。"""

    __tablename__ = "concept_technical_daily"
    __table_args__ = (
        Index(
            "idx_concept_technical_code_date",
            "ts_code",
            "trade_date",
            postgresql_ops={"trade_date": "DESC"},
        ),
        Index("idx_concept_technical_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    # 均线指标
    ma5: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    ma10: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    ma20: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    ma60: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    ma120: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    ma250: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # MACD 指标
    macd_dif: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    macd_dea: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    macd_hist: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # KDJ 指标
    kdj_k: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    kdj_d: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    kdj_j: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # RSI 指标
    rsi6: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    rsi12: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    rsi24: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # 布林带指标
    boll_upper: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    boll_mid: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    boll_lower: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # 成交量指标
    vol_ma5: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    vol_ma10: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    vol_ratio: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # 其他指标
    atr14: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    cci14: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    willr14: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
