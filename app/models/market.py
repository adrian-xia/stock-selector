from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TradeCalendar(Base):
    __tablename__ = "trade_calendar"

    cal_date: Mapped[date] = mapped_column(Date, primary_key=True)
    exchange: Mapped[str] = mapped_column(
        String(10), primary_key=True, default="SSE"
    )
    is_open: Mapped[bool] = mapped_column(Boolean, default=False)
    pre_trade_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class Stock(Base):
    __tablename__ = "stocks"

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    symbol: Mapped[str | None] = mapped_column(String(10), nullable=True)
    name: Mapped[str] = mapped_column(String(32))
    area: Mapped[str | None] = mapped_column(String(20), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(50), nullable=True)
    market: Mapped[str | None] = mapped_column(String(16), nullable=True)
    list_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    delist_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    list_status: Mapped[str] = mapped_column(String(4), default="L")
    is_hs: Mapped[str | None] = mapped_column(String(4), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class StockDaily(Base):
    __tablename__ = "stock_daily"
    __table_args__ = (
        Index("idx_stock_daily_code_date", "ts_code", "trade_date", postgresql_ops={"trade_date": "DESC"}),
        Index("idx_stock_daily_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    open: Mapped[float] = mapped_column(Numeric(10, 2))
    high: Mapped[float] = mapped_column(Numeric(10, 2))
    low: Mapped[float] = mapped_column(Numeric(10, 2))
    close: Mapped[float] = mapped_column(Numeric(10, 2))
    pre_close: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    pct_chg: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    vol: Mapped[float] = mapped_column(Numeric(20, 2), default=0)
    amount: Mapped[float] = mapped_column(Numeric(20, 2), default=0)
    adj_factor: Mapped[float | None] = mapped_column(Numeric(16, 6), nullable=True)
    turnover_rate: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    trade_status: Mapped[str] = mapped_column(String(4), default="1")
    data_source: Mapped[str] = mapped_column(String(16), default="tushare")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class StockMin(Base):
    __tablename__ = "stock_min"
    __table_args__ = (
        Index("idx_stock_min_code_time", "ts_code", "trade_time", postgresql_ops={"trade_time": "DESC"}),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_time: Mapped[datetime] = mapped_column(DateTime, primary_key=True)
    freq: Mapped[str] = mapped_column(String(8), primary_key=True, default="5min")
    open: Mapped[float] = mapped_column(Numeric(10, 2))
    high: Mapped[float] = mapped_column(Numeric(10, 2))
    low: Mapped[float] = mapped_column(Numeric(10, 2))
    close: Mapped[float] = mapped_column(Numeric(10, 2))
    vol: Mapped[float] = mapped_column(Numeric(20, 2), default=0)
    amount: Mapped[float] = mapped_column(Numeric(20, 2), default=0)
    data_source: Mapped[str] = mapped_column(String(16), default="tushare")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class StockSyncProgress(Base):
    """股票同步进度表（累积模型）。

    每只股票一条记录，追踪数据和指标分别同步到哪一天。
    status 支持 idle/syncing/computing/failed/delisted 五种状态。
    """

    __tablename__ = "stock_sync_progress"

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    # 数据同步进度：已同步到的最新日期，1900-01-01 表示从未同步
    data_date: Mapped[date] = mapped_column(
        Date, nullable=False, server_default="1900-01-01"
    )
    # 指标计算进度：已计算到的最新日期，1900-01-01 表示从未计算
    indicator_date: Mapped[date] = mapped_column(
        Date, nullable=False, server_default="1900-01-01"
    )
    # 当前状态：idle/syncing/computing/failed/delisted
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="idle"
    )
    # 失败重试次数
    retry_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    # 最近一次错误信息
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class RawSyncProgress(Base):
    """原始数据同步进度表。

    追踪各个 raw 表的同步进度，记录每张表最后同步到的日期。
    用于缺口检测和断点续传。
    """

    __tablename__ = "raw_sync_progress"

    # 表名（如 raw_tushare_daily, raw_tushare_fina_indicator）
    table_name: Mapped[str] = mapped_column(String(100), primary_key=True)
    # 最后同步日期
    last_sync_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # 最后同步行数
    last_sync_rows: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    # 更新时间
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )