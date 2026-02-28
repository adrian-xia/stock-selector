"""V4 回测引擎 — 逐日模拟量价配合策略。"""

import logging
from dataclasses import dataclass
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.strategy.filters.market_filter import MarketState, evaluate_market
from app.v4backtest.models import BacktestSignal

logger = logging.getLogger(__name__)

DEFAULT_PARAMS = {
    "accumulation_days": 60, "max_accumulation_range": 0.20,
    "min_t0_pct_chg": 6.0, "min_t0_vol_ratio": 2.5,
    "min_washout_days": 3, "max_washout_days": 8,
    "max_vol_shrink_ratio": 0.40, "max_tk_amplitude": 3.0,
    "ma_support_tolerance": 0.015,
    "market_index": "000300.SH", "market_filter_enabled": True,
}


@dataclass
class _WatchEntry:
    ts_code: str
    t0_date: date
    t0_close: float
    t0_open: float
    t0_low: float
    t0_volume: int
    t0_pct_chg: float
    washout_days: int = 0
    min_washout_vol: int = 0
    min_washout_low: float = 0.0
    status: str = "watching"


async def _get_trade_dates(session: AsyncSession, start: date, end: date) -> list[date]:
    r = await session.execute(text(
        "SELECT cal_date FROM trade_calendar WHERE is_open=true "
        "AND cal_date BETWEEN :s AND :e ORDER BY cal_date"
    ), {"s": start, "e": end})
    return [row[0] for row in r]


async def _fetch_daily_batch(session: AsyncSession, target_date: date) -> dict[str, dict]:
    """拉取当日全市场行情+技术指标，返回 {ts_code: {...}}。"""
    r = await session.execute(text("""
        SELECT sd.ts_code, sd.close, sd.open, sd.high, sd.low, sd.vol,
               sd.pct_chg, sd.turnover_rate,
               td.vol_ratio, td.ma10, td.ma20
        FROM stock_daily sd
        JOIN stocks s ON sd.ts_code = s.ts_code AND s.list_status='L'
        LEFT JOIN technical_daily td ON sd.ts_code=td.ts_code AND sd.trade_date=td.trade_date
        WHERE sd.trade_date = :d AND sd.vol > 0
    """), {"d": target_date})
    out = {}
    for row in r:
        out[row[0]] = {
            "close": float(row[1] or 0), "open": float(row[2] or 0),
            "high": float(row[3] or 0), "low": float(row[4] or 0),
            "vol": int(row[5] or 0), "pct_chg": float(row[6] or 0),
            "turnover_rate": float(row[7] or 0),
            "vol_ratio": float(row[8] or 0),
            "ma10": float(row[9] or 0), "ma20": float(row[10] or 0),
        }
    return out


async def _verify_accumulation_batch(
    session: AsyncSession, codes: list[str], target_date: date, params: dict
) -> set[str]:
    if not codes:
        return set()
    r = await session.execute(text(
        "SELECT cal_date FROM trade_calendar WHERE is_open=true AND cal_date<=:d "
        "ORDER BY cal_date DESC LIMIT 1 OFFSET :off"
    ), {"d": target_date, "off": params.get("accumulation_days", 60)})
    row = r.fetchone()
    if not row:
        return set()
    start_date = row[0]

    r2 = await session.execute(text(
        "SELECT cal_date FROM trade_calendar WHERE is_open=true AND cal_date<:d "
        "ORDER BY cal_date DESC LIMIT 1"
    ), {"d": target_date})
    prev = r2.fetchone()
    if not prev:
        return set()

    r3 = await session.execute(text("""
        SELECT ts_code FROM (
            SELECT ts_code, (MAX(high)-MIN(low))/NULLIF(MIN(low),0) AS amp
            FROM stock_daily WHERE ts_code=ANY(:codes)
              AND trade_date BETWEEN :s AND :p GROUP BY ts_code
        ) t WHERE amp <= :max_range
    """), {"codes": codes, "s": start_date, "p": prev[0],
           "max_range": params.get("max_accumulation_range", 0.20)})
    return {row[0] for row in r3}


def _verify_accumulation_from_memory(
    market_data: dict[date, dict[str, dict]],
    trade_dates: list[date],
    codes: list[str],
    target_date: date,
    params: dict,
) -> set[str]:
    """从内存数据验证吸筹条件，替代原来的 SQL 查询。"""
    acc_days = params.get("accumulation_days", 60)
    max_range = params.get("max_accumulation_range", 0.20)

    try:
        idx = trade_dates.index(target_date)
    except ValueError:
        return set()

    start_idx = max(0, idx - acc_days)
    lookback_dates = trade_dates[start_idx:idx]  # 不含当天

    valid = set()
    for code in codes:
        highs, lows = [], []
        for d in lookback_dates:
            s = market_data.get(d, {}).get(code)
            if s:
                highs.append(s["high"])
                lows.append(s["low"])
        if not lows:
            continue
        min_low = min(lows)
        if min_low <= 0:
            continue
        amplitude = (max(highs) - min_low) / min_low
        if amplitude <= max_range:
            valid.add(code)
    return valid


async def run_backtest(
    session: AsyncSession,
    params: dict | None = None,
    start_date: date = date(2024, 7, 1),
    end_date: date = date(2025, 12, 31),
    *,
    market_data: dict[date, dict[str, dict]] | None = None,
    t0_cache: dict[tuple, dict[date, list[str]]] | None = None,
    market_states: dict[date, str] | None = None,
    trade_dates: list[date] | None = None,
) -> list[BacktestSignal]:
    """逐日模拟量价配合策略，返回所有买入信号。

    Args:
        session: 数据库会话（有内存数据时仅用于 trade_dates 查询）
        params: 策略参数，None 时使用 DEFAULT_PARAMS
        start_date: 回测起始日期
        end_date: 回测结束日期
        market_data: 预加载的全市场行情 dict[date, dict[str, dict]]，有值时零 SQL
        t0_cache: 预计算的 T0 事件缓存 dict[tuple_key, dict[date, list[str]]]
        market_states: 预计算的大盘状态 dict[date, str]
        trade_dates: 预加载的交易日列表，有值时跳过 SQL 查询
    """
    p = {**DEFAULT_PARAMS, **(params or {})}

    # 交易日列表：优先用传入的，否则查 SQL
    if trade_dates is not None:
        tds = trade_dates
    else:
        tds = await _get_trade_dates(session, start_date, end_date)

    # T0 缓存 key（用于命中 t0_cache）
    t0_key = (p["min_t0_pct_chg"], p["min_t0_vol_ratio"], p["accumulation_days"])

    watchpool: dict[str, _WatchEntry] = {}
    signals: list[BacktestSignal] = []

    for td in tds:
        # 1. 大盘环境
        if market_states is not None:
            mkt = market_states.get(td, "neutral")
        elif p.get("market_filter_enabled"):
            mkt = (await evaluate_market(session, td, p.get("market_index", "000300.SH"))).value
        else:
            mkt = "neutral"

        if mkt == "bearish":
            continue

        # 2. 当日行情：优先内存，否则 SQL
        if market_data is not None:
            daily = market_data.get(td, {})
        else:
            daily = await _fetch_daily_batch(session, td)

        # 3. 扫描新 T0：优先 t0_cache，否则实时扫描
        if t0_cache is not None:
            t0_codes_raw = t0_cache.get(t0_key, {}).get(td, [])
            # 过滤掉已在观察池中的
            t0_codes = [c for c in t0_codes_raw if c not in watchpool]
        else:
            t0_codes = [
                code for code, d in daily.items()
                if d["pct_chg"] >= p["min_t0_pct_chg"]
                and d["vol_ratio"] >= p["min_t0_vol_ratio"]
                and code not in watchpool
            ]

        if t0_codes:
            # 吸筹验证：优先内存，否则 SQL
            if market_data is not None:
                valid = _verify_accumulation_from_memory(
                    market_data, tds, t0_codes, td, p
                )
            else:
                valid = await _verify_accumulation_batch(session, t0_codes, td, p)

            for code in valid:
                d = daily.get(code)
                if not d:
                    continue
                watchpool[code] = _WatchEntry(
                    ts_code=code, t0_date=td,
                    t0_close=d["close"], t0_open=d["open"],
                    t0_low=d["low"], t0_volume=d["vol"],
                    t0_pct_chg=d["pct_chg"],
                )

        # 4+5. 更新观察池 + 检测企稳
        to_remove = []
        for code, e in watchpool.items():
            if e.status != "watching":
                to_remove.append(code)
                continue
            d = daily.get(code)
            if not d:
                continue

            # 破位止损
            if d["low"] < e.t0_open:
                e.status = "stopped"
                to_remove.append(code)
                continue

            e.washout_days += 1
            e.min_washout_vol = min(d["vol"], e.min_washout_vol or d["vol"])
            e.min_washout_low = min(d["low"], e.min_washout_low or d["low"])

            if e.washout_days > p["max_washout_days"]:
                e.status = "expired"
                to_remove.append(code)
                continue

            # 企稳检测
            if e.washout_days >= p["min_washout_days"]:
                amp = (d["high"] - d["low"]) / d["close"] * 100 if d["close"] > 0 else 999
                vol_ratio = d["vol"] / e.t0_volume if e.t0_volume > 0 else 999
                ma_ok = False
                tol = p["ma_support_tolerance"]
                for ma_val in [d.get("ma10", 0), d.get("ma20", 0)]:
                    if ma_val > 0 and abs(d["low"] / ma_val - 1) <= tol:
                        ma_ok = True
                        break

                if (d["close"] > e.t0_open
                        and amp <= p["max_tk_amplitude"]
                        and vol_ratio <= p["max_vol_shrink_ratio"]
                        and ma_ok):
                    e.status = "triggered"
                    signals.append(BacktestSignal(
                        ts_code=code, signal_date=td, t0_date=e.t0_date,
                        entry_price=d["close"], market_state=mkt,
                    ))
                    to_remove.append(code)

        for code in to_remove:
            watchpool.pop(code, None)

    logger.info("[v4-backtest] 回测完成: %d 个信号 (%s ~ %s)", len(signals), start_date, end_date)
    return signals
