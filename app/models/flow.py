from datetime import date, datetime

from sqlalchemy import Date, DateTime, Index, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MoneyFlow(Base):
    __tablename__ = "money_flow"

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)

    buy_sm_vol: Mapped[float | None] = mapped_column(Numeric(20, 2), default=0)
    buy_sm_amount: Mapped[float | None] = mapped_column(Numeric(20, 2), default=0)
    sell_sm_vol: Mapped[float | None] = mapped_column(Numeric(20, 2), default=0)
    sell_sm_amount: Mapped[float | None] = mapped_column(Numeric(20, 2), default=0)
    buy_md_vol: Mapped[float | None] = mapped_column(Numeric(20, 2), default=0)
    buy_md_amount: Mapped[float | None] = mapped_column(Numeric(20, 2), default=0)
    sell_md_vol: Mapped[float | None] = mapped_column(Numeric(20, 2), default=0)
    sell_md_amount: Mapped[float | None] = mapped_column(Numeric(20, 2), default=0)
    buy_lg_vol: Mapped[float | None] = mapped_column(Numeric(20, 2), default=0)
    buy_lg_amount: Mapped[float | None] = mapped_column(Numeric(20, 2), default=0)
    sell_lg_vol: Mapped[float | None] = mapped_column(Numeric(20, 2), default=0)
    sell_lg_amount: Mapped[float | None] = mapped_column(Numeric(20, 2), default=0)
    buy_elg_vol: Mapped[float | None] = mapped_column(Numeric(20, 2), default=0)
    buy_elg_amount: Mapped[float | None] = mapped_column(Numeric(20, 2), default=0)
    sell_elg_vol: Mapped[float | None] = mapped_column(Numeric(20, 2), default=0)
    sell_elg_amount: Mapped[float | None] = mapped_column(Numeric(20, 2), default=0)
    net_mf_amount: Mapped[float | None] = mapped_column(Numeric(20, 2), default=0)

    data_source: Mapped[str] = mapped_column(String(16), default="tushare")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DragonTiger(Base):
    __tablename__ = "dragon_tiger"
    __table_args__ = (
        Index("idx_dragon_tiger_date", "trade_date"),
        Index("idx_dragon_tiger_code", "ts_code", "trade_date", postgresql_ops={"trade_date": "DESC"}),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts_code: Mapped[str] = mapped_column(String(16))
    trade_date: Mapped[date] = mapped_column(Date)
    reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    buy_total: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    sell_total: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    net_buy: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    list_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    data_source: Mapped[str] = mapped_column(String(16), default="tushare")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
