from datetime import date, datetime

from sqlalchemy import Boolean, DateTime, Date, Index, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TradePlan(Base):
    """交易计划：基于 T 日数据生成 T+1 触发条件。"""

    __tablename__ = "trade_plans"
    __table_args__ = (
        Index("idx_plan_date", "plan_date"),
        Index("idx_plan_code_date", "ts_code", "plan_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts_code: Mapped[str] = mapped_column(String(16), nullable=False)
    plan_date: Mapped[date] = mapped_column(Date, nullable=False)   # 生成日期（T日）
    valid_date: Mapped[date] = mapped_column(Date, nullable=False)  # 有效日期（T+1）

    # 触发条件
    direction: Mapped[str] = mapped_column(String(8), nullable=False, default="buy")
    trigger_type: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger_condition: Mapped[str] = mapped_column(Text, nullable=False)
    trigger_price: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)

    # 风控
    stop_loss: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    take_profit: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    risk_reward_ratio: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)

    # 来源
    source_strategy: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)

    # 执行结果（盘后回填）
    triggered: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    actual_price: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Strategy(Base):
    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    category: Mapped[str] = mapped_column(String(32))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    params: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class DataSourceConfig(Base):
    __tablename__ = "data_source_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_name: Mapped[str] = mapped_column(String(32), unique=True)
    priority: Mapped[int] = mapped_column(Integer, default=1)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    last_health_check: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class StrategyPick(Base):
    """策略选股记录：记录每次策略选出的股票，用于追踪后续涨跌表现。"""

    __tablename__ = "strategy_picks"
    __table_args__ = (
        Index("idx_picks_strategy_date", "strategy_name", "pick_date"),
        Index("idx_picks_date", "pick_date"),
        Index("idx_picks_code", "ts_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_name: Mapped[str] = mapped_column(String(64), nullable=False)  # 策略名
    pick_date: Mapped[date] = mapped_column(Date, nullable=False)            # 选股日期
    ts_code: Mapped[str] = mapped_column(String(16), nullable=False)         # 股票代码
    pick_score: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)   # 选股评分
    pick_close: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)   # 选股日收盘价

    # N日后收益追踪（盘后链路回填）
    return_1d: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)    # 1日收益率%
    return_3d: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)    # 3日收益率%
    return_5d: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)    # 5日收益率%
    return_10d: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)   # 10日收益率%
    return_20d: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)   # 20日收益率%
    max_return: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)   # 期间最大收益%
    max_drawdown: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True) # 期间最大回撤%

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class StrategyHitStat(Base):
    """策略命中率统计：按策略、日期、周期汇总命中率和收益分布。"""

    __tablename__ = "strategy_hit_stats"
    __table_args__ = (
        Index("idx_hit_stats_strategy", "strategy_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_name: Mapped[str] = mapped_column(String(64), nullable=False)
    stat_date: Mapped[date] = mapped_column(Date, nullable=False)    # 统计日期
    period: Mapped[str] = mapped_column(String(8), nullable=False)   # 统计周期: 1d/3d/5d/10d/20d
    total_picks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 总选股数
    win_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)    # 盈利数（收益>0）
    hit_rate: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)       # 命中率%
    avg_return: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)     # 平均收益率%
    median_return: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)  # 中位数收益率%
    best_return: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)    # 最佳收益率%
    worst_return: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)   # 最差收益率%

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
