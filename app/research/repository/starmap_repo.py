"""StarMap 数据仓库：表操作 UPSERT 封装。

统一封装 macro_signal_daily / sector_resonance_daily / trade_plan_daily_ext
三张表的读写操作。所有写入使用 UPSERT 保证幂等。
"""

import logging
from datetime import date
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.market import Stock
from app.models.starmap import MacroSignalDaily, SectorResonanceDaily, TradePlanDailyExt

logger = logging.getLogger(__name__)


class StarMapRepository:
    """StarMap 数据仓库。"""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    # -----------------------------------------------------------------------
    # macro_signal_daily
    # -----------------------------------------------------------------------

    async def upsert_macro_signal(self, data: dict[str, Any]) -> int:
        """UPSERT 宏观信号（以 trade_date 为幂等键）。

        Args:
            data: 字段字典

        Returns:
            受影响行数
        """
        stmt = pg_insert(MacroSignalDaily).values(**data)
        stmt = stmt.on_conflict_do_update(
            index_elements=["trade_date"],
            set_={
                k: stmt.excluded[k]
                for k in data
                if k not in ("id", "trade_date", "created_at")
            },
        )
        async with self._session_factory() as session:
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount

    async def get_macro_signal(self, trade_date: date) -> MacroSignalDaily | None:
        """查询指定日期的宏观信号。"""
        async with self._session_factory() as session:
            result = await session.execute(
                select(MacroSignalDaily).where(MacroSignalDaily.trade_date == trade_date)
            )
            return result.scalar_one_or_none()

    # -----------------------------------------------------------------------
    # sector_resonance_daily
    # -----------------------------------------------------------------------

    async def upsert_sector_resonance_batch(
        self, items: list[dict[str, Any]]
    ) -> int:
        """批量 UPSERT 行业共振评分。

        以 (trade_date, sector_code) 为幂等键。

        Args:
            items: 评分字典列表

        Returns:
            受影响行数
        """
        if not items:
            return 0

        total = 0
        async with self._session_factory() as session:
            for item in items:
                stmt = pg_insert(SectorResonanceDaily).values(**item)
                stmt = stmt.on_conflict_do_update(
                    constraint="uq_sector_resonance",
                    set_={
                        k: stmt.excluded[k]
                        for k in item
                        if k not in ("id", "trade_date", "sector_code", "created_at")
                    },
                )
                result = await session.execute(stmt)
                total += result.rowcount
            await session.commit()

        logger.info("行业共振 UPSERT: %d 条", total)
        return total

    async def get_sector_resonance(
        self, trade_date: date, top_n: int = 20
    ) -> list[SectorResonanceDaily]:
        """查询指定日期的行业共振排名。"""
        async with self._session_factory() as session:
            result = await session.execute(
                select(SectorResonanceDaily)
                .where(SectorResonanceDaily.trade_date == trade_date)
                .order_by(SectorResonanceDaily.final_score.desc())
                .limit(top_n)
            )
            return list(result.scalars().all())

    # -----------------------------------------------------------------------
    # trade_plan_daily_ext
    # -----------------------------------------------------------------------

    async def upsert_trade_plans_batch(
        self, items: list[dict[str, Any]]
    ) -> int:
        """批量 UPSERT 交易计划。

        以 (trade_date, ts_code, source_strategy) 为幂等键。

        Args:
            items: 交易计划字典列表

        Returns:
            受影响行数
        """
        if not items:
            return 0

        total = 0
        async with self._session_factory() as session:
            for item in items:
                stmt = pg_insert(TradePlanDailyExt).values(**item)
                stmt = stmt.on_conflict_do_update(
                    constraint="uq_trade_plan_ext",
                    set_={
                        k: stmt.excluded[k]
                        for k in item
                        if k not in ("id", "trade_date", "ts_code", "source_strategy", "created_at")
                    },
                )
                result = await session.execute(stmt)
                total += result.rowcount
            await session.commit()

        logger.info("交易计划 UPSERT: %d 条", total)
        return total

    async def get_trade_plans(
        self, trade_date: date, status: str | None = None
    ) -> list[TradePlanDailyExt]:
        """查询指定日期的交易计划。"""
        async with self._session_factory() as session:
            query = (
                select(TradePlanDailyExt, Stock.name)
                .outerjoin(Stock, Stock.ts_code == TradePlanDailyExt.ts_code)
                .where(TradePlanDailyExt.trade_date == trade_date)
            )
            if status:
                query = query.where(TradePlanDailyExt.plan_status == status)
            query = query.order_by(TradePlanDailyExt.confidence.desc())

            result = await session.execute(query)
            plans: list[TradePlanDailyExt] = []
            for plan, stock_name in result.all():
                setattr(plan, "stock_name", stock_name)
                plans.append(plan)
            return plans

    async def get_next_trade_date(self, current_date: date) -> date:
        """获取下一个交易日；若不存在则回退到当前日期。"""
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    """
                    SELECT cal_date
                    FROM trade_calendar
                    WHERE is_open = true
                      AND cal_date > :current_date
                    ORDER BY cal_date
                    LIMIT 1
                    """
                ),
                {"current_date": current_date},
            )
            row = result.fetchone()
            return row[0] if row else current_date

    # -----------------------------------------------------------------------
    # 跨表查询
    # -----------------------------------------------------------------------

    async def get_research_overview(self, trade_date: date) -> dict[str, Any]:
        """获取投研总览数据（供 API 使用）。

        Returns:
            包含 macro_signal, top_sectors, trade_plans 的字典
        """
        macro = await self.get_macro_signal(trade_date)
        sectors = await self.get_sector_resonance(trade_date, top_n=10)
        plans = await self.get_trade_plans(trade_date)

        def _normalize_sector_labels(items: Any) -> list[str]:
            if not items:
                return []
            result: list[str] = []
            for item in items:
                if isinstance(item, dict):
                    name = item.get("sector_name") or item.get("name")
                    if name:
                        result.append(str(name))
                elif item:
                    result.append(str(item))
            return result

        return {
            "trade_date": trade_date.isoformat(),
            "macro_signal": {
                "risk_appetite": macro.risk_appetite if macro else "unknown",
                "global_risk_score": float(macro.global_risk_score) if macro else 50.0,
                "summary": macro.macro_summary if macro else "无数据",
                "positive_sectors": _normalize_sector_labels(macro.positive_sectors) if macro else [],
                "negative_sectors": _normalize_sector_labels(macro.negative_sectors) if macro else [],
            },
            "top_sectors": [
                {
                    "sector_code": s.sector_code,
                    "sector_name": s.sector_name,
                    "final_score": float(s.final_score),
                    "news_score": float(s.news_score),
                    "moneyflow_score": float(s.moneyflow_score),
                    "trend_score": float(s.trend_score),
                    "confidence": float(s.confidence) if s.confidence is not None else 0.0,
                    "drivers": s.drivers or [],
                }
                for s in sectors
            ],
            "trade_plans": [
                {
                    "ts_code": p.ts_code,
                    "stock_name": getattr(p, "stock_name", None),
                    "valid_date": p.valid_date.isoformat() if p.valid_date else None,
                    "source_strategy": p.source_strategy,
                    "plan_type": p.plan_type,
                    "direction": p.direction,
                    "trigger_price": float(p.trigger_price) if p.trigger_price is not None else None,
                    "stop_loss_price": float(p.stop_loss_price) if p.stop_loss_price is not None else None,
                    "take_profit_price": float(p.take_profit_price) if p.take_profit_price is not None else None,
                    "risk_reward_ratio": float(p.risk_reward_ratio) if p.risk_reward_ratio is not None else None,
                    "confidence": float(p.confidence),
                    "position_suggestion": float(p.position_suggestion),
                    "market_regime": p.market_regime,
                    "market_risk_score": float(p.market_risk_score) if getattr(p, "market_risk_score", None) is not None else 0.0,
                    "sector_name": getattr(p, "sector_name", "") or "",
                    "sector_score": float(p.sector_score) if getattr(p, "sector_score", None) is not None else None,
                    "entry_rule": p.entry_rule,
                    "stop_loss_rule": p.stop_loss_rule,
                    "take_profit_rule": p.take_profit_rule,
                    "emergency_exit_text": getattr(p, "emergency_exit_text", "") or "",
                    "plan_status": p.plan_status,
                    "triggered": getattr(p, "triggered", None),
                    "actual_price": float(p.actual_price) if getattr(p, "actual_price", None) is not None else None,
                    "reasoning": getattr(p, "reasoning", None) or [],
                    "risk_flags": p.risk_flags or [],
                }
                for p in plans
            ],
        }
