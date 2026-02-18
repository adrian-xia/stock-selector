"""参数优化任务和结果的数据库模型。"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class OptimizationTask(Base):
    """参数优化任务表。"""

    __tablename__ = "optimization_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_name: Mapped[str] = mapped_column(String(64), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(16), nullable=False)  # grid / genetic
    param_space: Mapped[dict] = mapped_column(JSONB, nullable=False)
    stock_codes: Mapped[list] = mapped_column(JSONB, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    initial_capital: Mapped[float] = mapped_column(Numeric(20, 2), default=1_000_000)
    ga_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    top_n: Mapped[int] = mapped_column(Integer, default=20)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    total_combinations: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completed_combinations: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class OptimizationResult(Base):
    """参数优化结果表。"""

    __tablename__ = "optimization_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    params: Mapped[dict] = mapped_column(JSONB, nullable=False)
    sharpe_ratio: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    annual_return: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    max_drawdown: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    win_rate: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    total_trades: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_return: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    volatility: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    calmar_ratio: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    sortino_ratio: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
