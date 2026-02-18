"""指数数据模型。

包含指数基础信息、日线行情、成分股权重、行业分类等业务表。
"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class IndexBasic(Base):
    """指数基础信息表。"""

    __tablename__ = "index_basic"

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    fullname: Mapped[str | None] = mapped_column(String(128), nullable=True)
    market: Mapped[str | None] = mapped_column(String(16), nullable=True)
    publisher: Mapped[str | None] = mapped_column(String(64), nullable=True)
    index_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    category: Mapped[str | None] = mapped_column(String(16), nullable=True)
    base_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    base_point: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    list_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    weight_rule: Mapped[str | None] = mapped_column(String(128), nullable=True)
    desc: Mapped[str | None] = mapped_column(String(512), nullable=True)
    exp_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class IndexDaily(Base):
    """指数日线行情表。"""

    __tablename__ = "index_daily"
    __table_args__ = (
        Index(
            "idx_index_daily_code_date",
            "ts_code",
            "trade_date",
            postgresql_ops={"trade_date": "DESC"},
        ),
        Index("idx_index_daily_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    open: Mapped[float] = mapped_column(Numeric(12, 4))
    high: Mapped[float] = mapped_column(Numeric(12, 4))
    low: Mapped[float] = mapped_column(Numeric(12, 4))
    close: Mapped[float] = mapped_column(Numeric(12, 4))
    pre_close: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    change: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    pct_chg: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    vol: Mapped[float] = mapped_column(Numeric(20, 2), default=0)
    amount: Mapped[float] = mapped_column(Numeric(20, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class IndexWeight(Base):
    """指数成分股权重表。"""

    __tablename__ = "index_weight"
    __table_args__ = (
        Index("idx_index_weight_index_code", "index_code"),
        Index("idx_index_weight_trade_date", "trade_date"),
        Index("idx_index_weight_con_code", "con_code"),
    )

    index_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    con_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    weight: Mapped[float] = mapped_column(Numeric(10, 4))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class IndustryClassify(Base):
    """行业分类表。"""

    __tablename__ = "industry_classify"

    index_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    industry_name: Mapped[str] = mapped_column(String(64))
    level: Mapped[str] = mapped_column(String(4))
    industry_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    src: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class IndustryMember(Base):
    """行业成分股表。"""

    __tablename__ = "industry_member"
    __table_args__ = (
        Index("idx_industry_member_index_code", "index_code"),
        Index("idx_industry_member_con_code", "con_code"),
        Index("idx_industry_member_in_date", "in_date"),
    )

    index_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    con_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    in_date: Mapped[date] = mapped_column(Date, primary_key=True)
    out_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_new: Mapped[str | None] = mapped_column(String(4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class IndexTechnicalDaily(Base):
    """指数技术指标表。"""

    __tablename__ = "index_technical_daily"
    __table_args__ = (
        Index(
            "idx_index_technical_code_date",
            "ts_code",
            "trade_date",
            postgresql_ops={"trade_date": "DESC"},
        ),
        Index("idx_index_technical_trade_date", "trade_date"),
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
    # Extended indicators (V2 策略扩展)
    wr: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)  # Williams %R (14)
    cci: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)  # CCI (14)
    bias: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)  # BIAS (基于 MA20)
    obv: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)  # OBV 能量潮
    donchian_upper: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)  # 唐奇安上轨 (20)
    donchian_lower: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)  # 唐奇安下轨 (20)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
