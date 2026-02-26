"""P5 扩展数据业务表模型。

包含停复牌信息（suspend_info）和涨跌停统计（limit_list_daily）业务表。
"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Index, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SuspendInfo(Base):
    """停复牌信息业务表。"""

    __tablename__ = "suspend_info"
    __table_args__ = (
        Index("idx_suspend_info_ts_code", "ts_code"),
        Index("idx_suspend_info_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    suspend_timing: Mapped[str | None] = mapped_column(String(8), nullable=True)  # 停牌时间（上午/下午/全天）
    suspend_type: Mapped[str | None] = mapped_column(String(16), nullable=True)  # 停牌事由类别
    suspend_reason: Mapped[str | None] = mapped_column(String(256), nullable=True)  # 停牌原因
    resume_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # 复牌日期
    data_source: Mapped[str] = mapped_column(String(16), server_default="tushare")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class LimitListDaily(Base):
    """每日涨跌停统计业务表。"""

    __tablename__ = "limit_list_daily"
    __table_args__ = (
        Index(
            "idx_limit_list_daily_code_date",
            "ts_code",
            "trade_date",
            postgresql_ops={"trade_date": "DESC"},
        ),
        Index("idx_limit_list_daily_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)  # 股票名称
    close: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)  # 收盘价
    pct_chg: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)  # 涨跌幅
    amp: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)  # 振幅
    fc_ratio: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)  # 封单金额/流通市值
    fl_ratio: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)  # 封单手数/流通股本
    fd_amount: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)  # 封单金额
    first_time: Mapped[str | None] = mapped_column(String(8), nullable=True)  # 首次涨跌停时间
    last_time: Mapped[str | None] = mapped_column(String(8), nullable=True)  # 最后封板时间
    open_times: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 打开次数
    up_stat: Mapped[str | None] = mapped_column(String(16), nullable=True)  # 涨跌停统计（连板天数）
    limit_times: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 涨跌停次数
    data_source: Mapped[str] = mapped_column(String(16), server_default="tushare")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
