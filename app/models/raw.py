"""Tushare 原始数据表模型。

每个 Tushare 接口对应一张 raw_tushare_* 表，字段与 API 输出一一对应，不做任何转换。
日期字段保持 VARCHAR(8) 的 YYYYMMDD 格式，数值字段使用 NUMERIC。
每张表包含 fetched_at 时间戳，记录数据拉取时间。
"""

from datetime import datetime

from sqlalchemy import DateTime, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


# =====================================================================
# P0 核心原始表（6 张）
# =====================================================================


class RawTushareStockBasic(Base):
    """股票基础信息原始表（对应 stock_basic 接口）。"""

    __tablename__ = "raw_tushare_stock_basic"

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    symbol: Mapped[str | None] = mapped_column(String(10), nullable=True)
    name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    area: Mapped[str | None] = mapped_column(String(16), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(32), nullable=True)
    fullname: Mapped[str | None] = mapped_column(String(64), nullable=True)
    enname: Mapped[str | None] = mapped_column(String(128), nullable=True)
    cnspell: Mapped[str | None] = mapped_column(String(32), nullable=True)
    market: Mapped[str | None] = mapped_column(String(16), nullable=True)
    exchange: Mapped[str | None] = mapped_column(String(8), nullable=True)
    curr_type: Mapped[str | None] = mapped_column(String(8), nullable=True)
    list_status: Mapped[str | None] = mapped_column(String(4), nullable=True)
    list_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    delist_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    is_hs: Mapped[str | None] = mapped_column(String(4), nullable=True)
    act_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    act_ent_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
class RawTushareTradeCal(Base):
    """交易日历原始表（对应 trade_cal 接口）。"""

    __tablename__ = "raw_tushare_trade_cal"

    exchange: Mapped[str] = mapped_column(String(8), primary_key=True)
    cal_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    is_open: Mapped[str | None] = mapped_column(String(4), nullable=True)
    pretrade_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareDaily(Base):
    """A股日线行情原始表（对应 daily 接口）。"""

    __tablename__ = "raw_tushare_daily"
    __table_args__ = (
        Index("idx_raw_daily_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    open: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    high: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    low: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    close: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    pre_close: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    change: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    pct_chg: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    vol: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareAdjFactor(Base):
    """复权因子原始表（对应 adj_factor 接口）。"""

    __tablename__ = "raw_tushare_adj_factor"
    __table_args__ = (
        Index("idx_raw_adj_factor_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    adj_factor: Mapped[float | None] = mapped_column(Numeric(16, 6), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
class RawTushareDailyBasic(Base):
    """每日指标原始表（对应 daily_basic 接口）。

    包含 PE/PB/换手率/市值等基本面指标。
    """

    __tablename__ = "raw_tushare_daily_basic"
    __table_args__ = (
        Index("idx_raw_daily_basic_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    close: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    turnover_rate: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    turnover_rate_f: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    volume_ratio: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    pe: Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)
    pe_ttm: Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)
    pb: Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)
    ps: Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)
    ps_ttm: Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)
    dv_ratio: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    dv_ttm: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    total_share: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    float_share: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    free_share: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    total_mv: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    circ_mv: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareStkLimit(Base):
    """每日涨跌停价格原始表（对应 stk_limit 接口）。"""

    __tablename__ = "raw_tushare_stk_limit"
    __table_args__ = (
        Index("idx_raw_stk_limit_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    pre_close: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    up_limit: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    down_limit: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
