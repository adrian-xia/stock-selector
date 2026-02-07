from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BacktestTask(Base):
    __tablename__ = "backtest_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("strategies.id"), nullable=True
    )
    strategy_params: Mapped[dict] = mapped_column(JSONB, default=dict)
    stock_codes: Mapped[list] = mapped_column(JSONB, default=list)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    initial_capital: Mapped[float] = mapped_column(Numeric(20, 2), default=1_000_000)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class BacktestResult(Base):
    __tablename__ = "backtest_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("backtest_tasks.id"))
    total_return: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    annual_return: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    max_drawdown: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    sharpe_ratio: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    win_rate: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    profit_loss_ratio: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    total_trades: Mapped[int | None] = mapped_column(Integer, nullable=True)
    benchmark_return: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    alpha: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    beta: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    volatility: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    calmar_ratio: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    sortino_ratio: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    trades_json: Mapped[list] = mapped_column(JSONB, default=list)
    equity_curve_json: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
