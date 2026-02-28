"""全市场选股回放参数优化器。

通过历史交易日回放的方式评估策略参数组合的实际选股效果。
核心逻辑：对每组参数采样若干交易日执行选股管道，统计 5 日正收益占比和平均收益。

缓存优化：Layer 1-2 结果按日期缓存到 pipeline_cache 表，同一天多个参数组合共享缓存，
预期提速 10-20 倍。
"""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.optimization.param_space import count_combinations, generate_combinations
from app.strategy.pipeline import execute_pipeline

logger = logging.getLogger(__name__)


@dataclass
class MarketOptResult:
    """单组参数的优化评估结果。"""

    params: dict = field(default_factory=dict)
    hit_rate_5d: float = 0.0     # 5 日正收益占比
    avg_return_5d: float = 0.0   # 5 日平均收益率
    max_drawdown: float = 0.0    # 最大连续亏损
    total_picks: int = 0         # 总选股次数
    score: float = 0.0           # 综合评分


class MarketOptimizer:
    """全市场选股回放优化器。

    对每组参数在历史交易日上执行选股管道，收集选股结果后查询 T+5 收盘价
    计算实际收益率，最终按综合评分排序返回 Top N。

    缓存策略：
    - 每个采样日首次运行时，Pipeline Layer 1-2 结果写入 pipeline_cache
    - 后续参数组合直接从缓存读取 Layer 1-2，只重新计算 Layer 3-4
    - 大幅减少重复的 SQL 粗筛和技术指标计算

    Args:
        session_factory: 异步数据库会话工厂
        max_concurrency: 最大并发参数组合数
        sample_interval: 采样间隔天数
    """

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
        """执行全市场选股回放优化。

        Args:
            strategy_name: 策略名称
            param_space: 参数空间定义（与 param_space.py 格式一致）
            lookback_days: 回看交易日数
            top_n: 返回前 N 名结果
            progress_callback: 进度回调 (completed, total) -> None

        Returns:
            按 score 降序排列的 Top N 结果
        """
        # 1. 获取采样交易日
        sample_dates = await self._get_sample_dates(lookback_days)
        if not sample_dates:
            logger.warning("无可用交易日，跳过优化")
            return []

        # 2. 生成参数组合
        combinations = generate_combinations(param_space)
        total = len(combinations)
        logger.info(
            "开始全市场优化：策略=%s, 组合数=%d, 采样天数=%d（缓存模式）",
            strategy_name, total, len(sample_dates),
        )

        # 3. 预热缓存：对每个采样日先跑一次完整 Pipeline 填充 Layer 1-2 缓存 + 市场快照
        snapshot_cache: dict = {}
        layer_cache: dict = {}
        logger.info("预热 Pipeline 缓存：%d 个采样日...", len(sample_dates))
        await self._warmup_cache(strategy_name, sample_dates, snapshot_cache, layer_cache)
        logger.info("缓存预热完成（快照缓存 %d 天）", len(snapshot_cache))

        # 4. 并发评估每组参数（复用缓存）
        completed = 0
        results: list[MarketOptResult] = []

        async def _evaluate_one(params: dict) -> MarketOptResult:
            nonlocal completed
            async with self._semaphore:
                result = await self._evaluate_params(
                    strategy_name, params, sample_dates, snapshot_cache, layer_cache,
                )
                completed += 1
                if progress_callback:
                    try:
                        progress_callback(completed, total)
                    except Exception:
                        pass
                return result

        tasks = [_evaluate_one(combo) for combo in combinations]
        results = await asyncio.gather(*tasks)

        # 5. 按 score 降序排列
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_n]

    async def _warmup_cache(
        self,
        strategy_name: str,
        sample_dates: list[date],
        snapshot_cache: dict | None = None,
        layer_cache: dict | None = None,
    ) -> None:
        """对每个采样日执行一次完整 Pipeline，填充 Layer 1-2 缓存 + 市场快照缓存。

        使用默认参数（空参数）跑一次，目的是写入缓存，后续参数组合直接复用。
        已有缓存的日期会被 ON CONFLICT DO NOTHING 跳过，不重复计算。
        """
        warmup_sem = asyncio.Semaphore(4)

        async def _warmup_one(target_date: date) -> None:
            async with warmup_sem:
                try:
                    await execute_pipeline(
                        session_factory=self._session_factory,
                        strategy_names=[strategy_name],
                        target_date=target_date,
                        top_n=1,
                        strategy_params=None,
                        use_cache=True,
                        snapshot_cache=snapshot_cache,
                        layer_cache=layer_cache,
                    )
                except Exception as e:
                    logger.warning("缓存预热失败 date=%s: %s", target_date, e)

        await asyncio.gather(*[_warmup_one(d) for d in sample_dates])

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

        # 间隔采样
        sample = all_dates[::self._sample_interval]
        sample.reverse()  # 按时间升序
        return sample

    async def _evaluate_params(
        self,
        strategy_name: str,
        params: dict,
        sample_dates: list[date],
        snapshot_cache: dict | None = None,
        layer_cache: dict | None = None,
    ) -> MarketOptResult:
        """评估单组参数在采样交易日上的选股效果（复用 Layer 1-2 缓存 + 快照缓存）。"""
        all_returns: list[float] = []
        total_picks = 0

        for target_date in sample_dates:
            try:
                pipeline_result = await execute_pipeline(
                    session_factory=self._session_factory,
                    strategy_names=[strategy_name],
                    target_date=target_date,
                    top_n=50,
                    strategy_params={strategy_name: params} if params else None,
                    use_cache=True,
                    snapshot_cache=snapshot_cache,
                    layer_cache=layer_cache,
                )

                if not pipeline_result.picks:
                    continue

                ts_codes = [p.ts_code for p in pipeline_result.picks]
                total_picks += len(ts_codes)

                returns_5d = await self._calc_returns(ts_codes, target_date, days=5)
                all_returns.extend(returns_5d)

            except Exception as e:
                logger.debug("评估失败 date=%s params=%s: %s", target_date, params, e)
                continue

        if not all_returns:
            return MarketOptResult(params=params)

        hit_count = sum(1 for r in all_returns if r > 0)
        hit_rate_5d = hit_count / len(all_returns) if all_returns else 0.0
        avg_return_5d = sum(all_returns) / len(all_returns) if all_returns else 0.0

        negative_returns = [r for r in all_returns if r < 0]
        max_drawdown = abs(min(negative_returns)) if negative_returns else 0.0

        score = hit_rate_5d * 0.5 + avg_return_5d * 0.3 - max_drawdown * 0.2

        return MarketOptResult(
            params=params,
            hit_rate_5d=round(hit_rate_5d, 6),
            avg_return_5d=round(avg_return_5d, 6),
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

            target_date_n = future_dates[-1]

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
                {
                    "buy_date": base_date,
                    "sell_date": target_date_n,
                    "codes": ts_codes,
                },
            )
            rows = result.fetchall()

        returns = []
        for row in rows:
            buy_close = float(row[1])
            sell_close = float(row[2])
            ret = (sell_close - buy_close) / buy_close
            returns.append(ret)

        return returns

