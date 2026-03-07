"""全市场选股回放参数优化器。

当前仅支持 V2 trigger 策略，通过历史交易日回放 V2 Pipeline 评估参数组合。
"""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.optimization.param_space import generate_combinations
from app.strategy.pipeline_v2 import execute_pipeline_v2

logger = logging.getLogger(__name__)


@dataclass
class MarketOptResult:
    """单组参数的优化评估结果。"""

    params: dict = field(default_factory=dict)
    hit_rate_5d: float = 0.0
    avg_return_5d: float = 0.0
    profit_loss_ratio: float = 0.0
    max_drawdown: float = 0.0
    total_picks: int = 0
    score: float = 0.0


class MarketOptimizer:
    """V2 全市场选股回放优化器。"""

    def __init__(
        self,
        session_factory: async_sessionmaker,
        max_concurrency: int = 8,
        sample_interval: int = 4,
    ) -> None:
        self._session_factory = session_factory
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._sample_interval = sample_interval

    async def optimize(
        self,
        strategy_name: str,
        param_space: dict,
        lookback_days: int = 120,
        top_n: int = 10,
        progress_callback: Callable | None = None,
    ) -> list[MarketOptResult]:
        """执行全市场 V2 trigger 参数优化。"""
        sample_dates = await self._get_sample_dates(lookback_days)
        if not sample_dates:
            logger.warning("无可用交易日，跳过优化")
            return []

        combinations = generate_combinations(param_space)
        total = len(combinations)
        if total == 0:
            return []

        logger.info(
            "开始全市场优化：策略=%s, 组合数=%d, 采样天数=%d",
            strategy_name,
            total,
            len(sample_dates),
        )

        returns_cache: dict[tuple[date, str], float] = {}
        await self._warmup_returns(sample_dates, returns_cache)

        completed = 0

        async def _evaluate_one(params: dict) -> MarketOptResult:
            nonlocal completed
            async with self._semaphore:
                try:
                    result = await self._evaluate_params(
                        strategy_name=strategy_name,
                        params=params,
                        sample_dates=sample_dates,
                        returns_cache=returns_cache,
                    )
                except Exception as exc:
                    logger.error("参数评估异常 params=%s: %s", params, exc)
                    result = MarketOptResult(params=params)

                completed += 1
                if progress_callback:
                    try:
                        progress_callback(completed, total)
                    except Exception:
                        pass
                return result

        results = await asyncio.gather(*[_evaluate_one(params) for params in combinations])
        results.sort(key=lambda item: item.score, reverse=True)
        return results[:top_n]

    async def _get_sample_dates(self, lookback_days: int) -> list[date]:
        """从交易日历获取采样日期。"""
        async with self._session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT cal_date FROM trade_calendar
                    WHERE is_open = true AND cal_date <= CURRENT_DATE
                    ORDER BY cal_date DESC
                    LIMIT :limit
                """),
                {"limit": lookback_days},
            )
            all_dates = [row[0] for row in result.fetchall()]

        if not all_dates:
            return []

        sample_dates = all_dates[::self._sample_interval]
        sample_dates.reverse()
        return sample_dates

    async def _evaluate_params(
        self,
        strategy_name: str,
        params: dict,
        sample_dates: list[date],
        snapshot_cache: dict | None = None,
        layer_cache: dict | None = None,
        finance_cache: dict | None = None,
        returns_cache: dict | None = None,
    ) -> MarketOptResult:
        """评估单组参数在采样交易日上的选股效果。"""
        del snapshot_cache, layer_cache, finance_cache

        all_returns: list[float] = []
        total_picks = 0

        for target_date in sample_dates:
            try:
                pipeline_result = await execute_pipeline_v2(
                    session_factory=self._session_factory,
                    target_date=target_date,
                    trigger_names=[strategy_name],
                    strategy_params={strategy_name: params} if params else None,
                    top_n=50,
                )
            except Exception as exc:
                logger.debug("评估失败 date=%s params=%s: %s", target_date, params, exc)
                continue

            if not pipeline_result.picks:
                continue

            ts_codes = [pick.ts_code for pick in pipeline_result.picks]
            total_picks += len(ts_codes)

            if returns_cache is not None:
                for code in ts_codes:
                    cached = returns_cache.get((target_date, code))
                    if cached is not None:
                        all_returns.append(cached)
            else:
                all_returns.extend(await self._calc_returns(ts_codes, target_date, days=5))

        if not all_returns:
            return MarketOptResult(params=params)

        hit_count = sum(1 for value in all_returns if value > 0)
        hit_rate_5d = hit_count / len(all_returns)
        avg_return_5d = sum(all_returns) / len(all_returns)

        positive_returns = [value for value in all_returns if value > 0]
        negative_returns = [value for value in all_returns if value < 0]
        max_drawdown = abs(min(negative_returns)) if negative_returns else 0.0
        avg_gain = sum(positive_returns) / len(positive_returns) if positive_returns else 0.0
        avg_loss = abs(sum(negative_returns) / len(negative_returns)) if negative_returns else 0.0

        if avg_gain > 0 and avg_loss == 0:
            profit_loss_ratio = 3.0
        elif avg_gain > 0 and avg_loss > 0:
            profit_loss_ratio = avg_gain / avg_loss
        else:
            profit_loss_ratio = 0.0

        score = hit_rate_5d * 0.4 + profit_loss_ratio * 0.35 - max_drawdown * 0.25

        return MarketOptResult(
            params=params,
            hit_rate_5d=round(hit_rate_5d, 6),
            avg_return_5d=round(avg_return_5d, 6),
            profit_loss_ratio=round(profit_loss_ratio, 6),
            max_drawdown=round(max_drawdown, 6),
            total_picks=total_picks,
            score=round(score, 6),
        )

    async def _calc_returns(
        self,
        ts_codes: list[str],
        base_date: date,
        days: int = 5,
    ) -> list[float]:
        """计算股票在 base_date 买入后 N 个交易日的收益率。"""
        if not ts_codes:
            return []

        async with self._session_factory() as session:
            future_result = await session.execute(
                text("""
                    SELECT cal_date FROM trade_calendar
                    WHERE is_open = true AND cal_date > :base_date
                    ORDER BY cal_date
                    LIMIT :days
                """),
                {"base_date": base_date, "days": days},
            )
            future_dates = [row[0] for row in future_result.fetchall()]
            if not future_dates:
                return []

            sell_date = future_dates[-1]
            result = await session.execute(
                text("""
                    SELECT
                        b.ts_code,
                        b.close AS buy_close,
                        s.close AS sell_close
                    FROM stock_daily b
                    JOIN stock_daily s ON b.ts_code = s.ts_code AND s.trade_date = :sell_date
                    WHERE b.trade_date = :buy_date
                      AND b.ts_code = ANY(:codes)
                      AND b.close > 0
                      AND s.close > 0
                """),
                {"buy_date": base_date, "sell_date": sell_date, "codes": ts_codes},
            )
            rows = result.fetchall()

        returns: list[float] = []
        for row in rows:
            buy_close = float(row[1])
            sell_close = float(row[2])
            returns.append((sell_close - buy_close) / buy_close)
        return returns

    async def _warmup_returns(
        self,
        sample_dates: list[date],
        returns_cache: dict,
        days: int = 5,
    ) -> None:
        """预热所有采样日的 N 日收益率缓存。"""
        async with self._session_factory() as session:
            for base_date in sample_dates:
                future_result = await session.execute(
                    text("""
                        SELECT cal_date FROM trade_calendar
                        WHERE is_open = true AND cal_date > :base_date
                        ORDER BY cal_date
                        LIMIT :days
                    """),
                    {"base_date": base_date, "days": days},
                )
                future_dates = [row[0] for row in future_result.fetchall()]
                if not future_dates:
                    continue

                sell_date = future_dates[-1]
                result = await session.execute(
                    text("""
                        SELECT
                            b.ts_code,
                            b.close AS buy_close,
                            s.close AS sell_close
                        FROM stock_daily b
                        JOIN stock_daily s ON b.ts_code = s.ts_code AND s.trade_date = :sell_date
                        WHERE b.trade_date = :buy_date
                          AND b.close > 0
                          AND s.close > 0
                    """),
                    {"buy_date": base_date, "sell_date": sell_date},
                )
                for row in result.fetchall():
                    buy_close = float(row[1])
                    sell_close = float(row[2])
                    returns_cache[(base_date, row[0])] = (sell_close - buy_close) / buy_close
