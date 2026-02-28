"""V4 参数网格搜索。

支持两种模式：
1. 传统模式：每组参数独立查 SQL（向后兼容）
2. 零 SQL 模式：预加载全量数据到内存，回测阶段零 SQL（网格搜索默认）
"""

import asyncio
import itertools
import logging
import time
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.strategy.filters.market_filter import evaluate_market
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
    """逐条填充信号的后续收益（SQL 版本，向后兼容）。"""
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


# ── 零 SQL 预加载函数 ──


async def _preload_market_data(
    session: AsyncSession, start_date: date, end_date: date,
) -> dict[date, dict[str, dict]]:
    """一次性加载全部交易日的全市场行情到内存。

    数据量：~400 天 × ~5000 股 × 11 字段 ≈ 200 万行
    内存占用：约 1-2 GB | 加载耗时：约 10-15 秒
    """
    t0 = time.monotonic()
    r = await session.execute(text("""
        SELECT sd.trade_date, sd.ts_code, sd.close, sd.open,
               sd.high, sd.low, sd.vol, sd.pct_chg, sd.turnover_rate,
               td.vol_ratio, td.ma10, td.ma20
        FROM stock_daily sd
        JOIN stocks s ON sd.ts_code = s.ts_code AND s.list_status='L'
        LEFT JOIN technical_daily td
            ON sd.ts_code=td.ts_code AND sd.trade_date=td.trade_date
        WHERE sd.trade_date BETWEEN :start AND :end AND sd.vol > 0
        ORDER BY sd.trade_date, sd.ts_code
    """), {"start": start_date, "end": end_date})

    market_data: dict[date, dict[str, dict]] = {}
    row_count = 0
    for row in r:
        d = row[0]
        if d not in market_data:
            market_data[d] = {}
        market_data[d][row[1]] = {
            "close": float(row[2] or 0), "open": float(row[3] or 0),
            "high": float(row[4] or 0), "low": float(row[5] or 0),
            "vol": int(row[6] or 0), "pct_chg": float(row[7] or 0),
            "turnover_rate": float(row[8] or 0),
            "vol_ratio": float(row[9] or 0),
            "ma10": float(row[10] or 0), "ma20": float(row[11] or 0),
        }
        row_count += 1

    elapsed = time.monotonic() - t0
    logger.info(
        "[preload] 行情数据: %d 天, %d 行, 耗时 %.1fs",
        len(market_data), row_count, elapsed,
    )
    return market_data


def _precompute_t0_events(
    market_data: dict[date, dict[str, dict]],
    front_params_combos: list[dict],
) -> dict[tuple, dict[date, list[str]]]:
    """预计算所有前端参数组合的 T0 事件。

    缓存 key: (min_t0_pct_chg, min_t0_vol_ratio, accumulation_days)
    """
    t0 = time.monotonic()
    cache: dict[tuple, dict[date, list[str]]] = {}
    for fp in front_params_combos:
        key = (
            fp.get("min_t0_pct_chg", 6.0),
            fp.get("min_t0_vol_ratio", 2.5),
            fp.get("accumulation_days", 60),
        )
        if key in cache:
            continue
        t0_by_date: dict[date, list[str]] = {}
        for d, stocks in market_data.items():
            codes = [
                code for code, s in stocks.items()
                if s["pct_chg"] >= key[0] and s["vol_ratio"] >= key[1]
            ]
            if codes:
                t0_by_date[d] = codes
        cache[key] = t0_by_date

    elapsed = time.monotonic() - t0
    logger.info("[preload] T0 预计算: %d 种前端参数, 耗时 %.1fs", len(cache), elapsed)
    return cache


async def _preload_market_states(
    session: AsyncSession,
    trade_dates: list[date],
    index_code: str = "000300.SH",
) -> dict[date, str]:
    """预计算所有交易日的大盘状态。"""
    t0 = time.monotonic()
    states: dict[date, str] = {}
    for d in trade_dates:
        state = await evaluate_market(session, d, index_code)
        states[d] = state.value
    elapsed = time.monotonic() - t0
    logger.info("[preload] 大盘状态: %d 天, 耗时 %.1fs", len(states), elapsed)
    return states


def _fill_returns_from_memory(
    signals: list[BacktestSignal],
    market_data: dict[date, dict[str, dict]],
    trade_dates: list[date],
) -> None:
    """从内存数据计算信号后续收益，替代逐条 SQL 查询。"""
    if not signals:
        return
    date_index = {d: i for i, d in enumerate(trade_dates)}
    for sig in signals:
        idx = date_index.get(sig.signal_date)
        if idx is None:
            continue
        ep = sig.entry_price
        if ep <= 0:
            continue
        future = trade_dates[idx + 1:]
        for offset, attr in [(1, "ret_1d"), (3, "ret_3d"),
                             (5, "ret_5d"), (10, "ret_10d")]:
            if offset <= len(future):
                d = future[offset - 1]
                s = market_data.get(d, {}).get(sig.ts_code)
                if s and s["close"] > 0:
                    setattr(sig, attr, s["close"] / ep - 1)


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

    # ── 预加载阶段（3 次 SQL，之后零 SQL）──
    t_start = time.monotonic()
    async with session_factory() as session:
        # 1. 交易日列表
        r = await session.execute(text(
            "SELECT cal_date FROM trade_calendar WHERE is_open=true "
            "AND cal_date BETWEEN :s AND :e ORDER BY cal_date"
        ), {"s": start_date, "e": end_date})
        trade_dates = [row[0] for row in r]

        # 2. 全市场行情
        market_data = await _preload_market_data(session, start_date, end_date)

        # 3. 大盘状态
        market_states = await _preload_market_states(session, trade_dates)

    # 4. T0 预计算（纯内存）
    t0_cache = _precompute_t0_events(market_data, combos)

    preload_elapsed = time.monotonic() - t_start
    logger.info("[grid-search] 预加载完成, 耗时 %.1fs", preload_elapsed)

    # ── 网格搜索阶段（零 SQL）──
    sem = asyncio.Semaphore(max_concurrency)

    async def _run_one(params: dict) -> GridSearchResult | None:
        async with sem:
            try:
                async with session_factory() as session:
                    sigs = await run_backtest(
                        session, params, start_date, end_date,
                        market_data=market_data,
                        t0_cache=t0_cache,
                        market_states=market_states,
                        trade_dates=trade_dates,
                    )
                    _fill_returns_from_memory(sigs, market_data, trade_dates)
                    metrics = evaluate_signals(sigs)
                    return GridSearchResult(params=params, metrics=metrics)
            except Exception:
                logger.exception("[grid-search] 参数组合失败: %s", params)
                return None

    tasks = [_run_one(p) for p in combos]
    raw = await asyncio.gather(*tasks)
    results = [r for r in raw if r is not None]

    total_elapsed = time.monotonic() - t_start
    logger.info(
        "[grid-search] 完成: %d/%d 组成功, 总耗时 %.1fs (预加载 %.1fs)",
        len(results), len(combos), total_elapsed, preload_elapsed,
    )
    return rank_results(results)


