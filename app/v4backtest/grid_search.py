"""V4 参数网格搜索。"""

import asyncio
import itertools
import logging
from datetime import date
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.v4backtest.engine import run_backtest
from app.v4backtest.evaluator import evaluate_signals
from app.v4backtest.models import BacktestSignal, GridSearchResult
from app.v4backtest.queries import CALC_RETURNS_SQL

logger = logging.getLogger(__name__)

PARAM_GRID = {
    "accumulation_days": [30, 45, 60],
    "min_t0_pct_chg": [5.0, 6.0, 7.0],
    "min_t0_vol_ratio": [2.0, 2.5, 3.0],
    "min_washout_days": [2, 3, 4],
    "max_washout_days": [6, 8, 10],
    "max_vol_shrink_ratio": [0.30, 0.40, 0.50],
    "max_tk_amplitude": [2.0, 3.0, 4.0],
    "ma_support_tolerance": [0.010, 0.015, 0.020],
}


def generate_param_grid(grid: dict | None = None) -> list[dict]:
    g = grid or PARAM_GRID
    keys = list(g.keys())
    return [dict(zip(keys, combo)) for combo in itertools.product(*g.values())]


async def fill_returns(session, signals: list[BacktestSignal]) -> None:
    """逐条填充信号的后续收益。"""
    if not signals:
        return
    for s in signals:
        row = (await session.execute(
            text(CALC_RETURNS_SQL), {"code": s.ts_code, "sig_date": s.signal_date}
        )).fetchone()
        if not row:
            continue
        ep = s.entry_price
        if ep <= 0:
            continue
        s.ret_1d = (float(row.c1) / ep - 1) if row.c1 else None
        s.ret_3d = (float(row.c3) / ep - 1) if row.c3 else None
        s.ret_5d = (float(row.c5) / ep - 1) if row.c5 else None
        s.ret_10d = (float(row.c10) / ep - 1) if row.c10 else None


def rank_results(results: list[GridSearchResult]) -> list[GridSearchResult]:
    for r in results:
        m = r.metrics
        r.score = round(
            (m.win_rate_5d or 0) * 0.4
            + min(m.profit_loss_ratio or 0, 5) / 5 * 0.3
            + min(m.sharpe_ratio or 0, 3) / 3 * 0.3,
            4,
        )
    return sorted(results, key=lambda r: r.score, reverse=True)


async def run_grid_search(
    session_factory: async_sessionmaker,
    start_date: date = date(2024, 7, 1),
    end_date: date = date(2025, 12, 31),
    param_grid: dict | None = None,
    max_concurrency: int = 8,
) -> list[GridSearchResult]:
    combos = generate_param_grid(param_grid)
    logger.info("[grid-search] %d 组参数, 并发度 %d", len(combos), max_concurrency)
    sem = asyncio.Semaphore(max_concurrency)
    results: list[GridSearchResult] = []

    async def _run_one(params: dict) -> GridSearchResult | None:
        async with sem:
            try:
                async with session_factory() as session:
                    sigs = await run_backtest(session, params, start_date, end_date)
                    await fill_returns(session, sigs)
                    metrics = evaluate_signals(sigs)
                    return GridSearchResult(params=params, metrics=metrics)
            except Exception:
                logger.exception("[grid-search] 参数组合失败: %s", params)
                return None

    tasks = [_run_one(p) for p in combos]
    raw = await asyncio.gather(*tasks)
    results = [r for r in raw if r is not None]
    return rank_results(results)
