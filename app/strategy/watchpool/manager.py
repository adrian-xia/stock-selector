"""观察池管理器 — strategy_watchpool 表的 CRUD + 状态流转。"""

import logging
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

INSERT_T0_SQL = text("""
    INSERT INTO strategy_watchpool
        (ts_code, strategy_name, t0_date, t0_close, t0_open, t0_low, t0_volume, t0_pct_chg,
         sector_score, market_score)
    VALUES (:ts_code, :strategy_name, :t0_date, :t0_close, :t0_open, :t0_low, :t0_volume,
            :t0_pct_chg, :sector_score, :market_score)
    ON CONFLICT ON CONSTRAINT uq_watchpool_code_date_strategy DO NOTHING
""")

WATCHING_WITH_TODAY_SQL = text("""
    SELECT w.id, w.ts_code, w.t0_open, w.t0_low, w.t0_volume,
           w.washout_days, w.min_washout_vol, w.min_washout_low,
           sd.close, sd.low, sd.high, sd.vol AS today_vol
    FROM strategy_watchpool w
    JOIN stock_daily sd ON w.ts_code = sd.ts_code
    WHERE w.status = 'watching'
      AND w.t0_date < :target_date
      AND sd.trade_date = :target_date
""")

STABILIZATION_SQL = text("""
    SELECT w.id, w.ts_code, w.t0_volume, w.t0_open, w.washout_days,
           sd.close, sd.open, sd.high, sd.low, sd.vol AS today_vol,
           td.ma10, td.ma20,
           CASE WHEN sd.close > 0 THEN (sd.high - sd.low) / sd.close * 100 ELSE 999 END AS amplitude,
           CASE WHEN w.t0_volume > 0 THEN sd.vol::float / w.t0_volume ELSE 999 END AS vol_shrink_ratio
    FROM strategy_watchpool w
    JOIN stock_daily sd ON w.ts_code = sd.ts_code AND sd.trade_date = :target_date
    JOIN technical_daily td ON w.ts_code = td.ts_code AND td.trade_date = :target_date
    WHERE w.status = 'watching'
      AND w.t0_date < :target_date
      AND w.washout_days >= :min_days
      AND sd.close > w.t0_open
      AND CASE WHEN sd.close > 0 THEN (sd.high - sd.low) / sd.close * 100 ELSE 999 END <= :max_amp
      AND CASE WHEN w.t0_volume > 0 THEN sd.vol::float / w.t0_volume ELSE 999 END <= :max_vol_ratio
      AND (
          ABS(sd.low / NULLIF(td.ma10, 0) - 1) <= :ma_tolerance
          OR ABS(sd.low / NULLIF(td.ma20, 0) - 1) <= :ma_tolerance
      )
""")

ACCUMULATION_CHECK_SQL = text("""
    SELECT ts_code,
           (MAX(high) - MIN(low)) / NULLIF(MIN(low), 0) AS amplitude
    FROM stock_daily
    WHERE ts_code = ANY(:codes)
      AND trade_date BETWEEN :start_date AND :prev_date
    GROUP BY ts_code
    HAVING (MAX(high) - MIN(low)) / NULLIF(MIN(low), 0) <= :max_range
""")

TRADE_DATE_OFFSET_SQL = text("""
    SELECT cal_date FROM trade_calendar
    WHERE is_open = true AND cal_date <= :ref_date
    ORDER BY cal_date DESC
    LIMIT 1 OFFSET :offset
""")


async def get_trade_date_offset(session: AsyncSession, ref_date: date, offset: int) -> date | None:
    row = (await session.execute(TRADE_DATE_OFFSET_SQL, {"ref_date": ref_date, "offset": offset})).fetchone()
    return row.cal_date if row else None


async def verify_accumulation(
    session: AsyncSession, codes: list[str], target_date: date, params: dict
) -> set[str]:
    """批量验证吸筹条件，返回通过的 ts_code 集合。"""
    if not codes:
        return set()
    start_date = await get_trade_date_offset(session, target_date, params.get("accumulation_days", 60))
    if not start_date:
        return set()
    prev_date = await get_trade_date_offset(session, target_date, 1)
    if not prev_date:
        return set()
    rows = await session.execute(ACCUMULATION_CHECK_SQL, {
        "codes": codes, "start_date": start_date, "prev_date": prev_date,
        "max_range": params.get("max_accumulation_range", 0.20),
    })
    return {r.ts_code for r in rows}


async def insert_t0_batch(
    session: AsyncSession, entries: list[dict]
) -> int:
    """批量写入新 T0 事件到观察池。"""
    count = 0
    for e in entries:
        await session.execute(INSERT_T0_SQL, e)
        count += 1
    return count


async def update_watchpool(
    session: AsyncSession, target_date: date, params: dict
) -> dict[str, int]:
    """批量更新观察池状态，返回各状态计数。"""
    rows = (await session.execute(WATCHING_WITH_TODAY_SQL, {"target_date": target_date})).fetchall()
    stats = {"stopped": 0, "expired": 0, "updated": 0}
    stopped_ids, expired_ids = [], []
    update_batch = []

    max_days = params.get("max_washout_days", 8)

    for item in rows:
        # 价格跌破 T0 底线 → stopped
        if float(item.low) < float(item.t0_open):
            stopped_ids.append(item.id)
            continue
        new_days = (item.washout_days or 0) + 1
        if new_days > max_days:
            expired_ids.append(item.id)
            continue
        min_vol = min(int(item.today_vol), int(item.min_washout_vol or item.today_vol))
        min_low = min(float(item.low), float(item.min_washout_low or item.low))
        update_batch.append((item.id, new_days, min_vol, min_low))

    if stopped_ids:
        await session.execute(text(
            "UPDATE strategy_watchpool SET status='stopped', updated_at=:d WHERE id = ANY(:ids)"
        ), {"ids": stopped_ids, "d": target_date})
        stats["stopped"] = len(stopped_ids)

    if expired_ids:
        await session.execute(text(
            "UPDATE strategy_watchpool SET status='expired', updated_at=:d WHERE id = ANY(:ids)"
        ), {"ids": expired_ids, "d": target_date})
        stats["expired"] = len(expired_ids)

    for wid, days, mvol, mlow in update_batch:
        await session.execute(text(
            "UPDATE strategy_watchpool SET washout_days=:d, min_washout_vol=:v, "
            "min_washout_low=:l, updated_at=:dt WHERE id=:id"
        ), {"id": wid, "d": days, "v": mvol, "l": mlow, "dt": target_date})
    stats["updated"] = len(update_batch)

    return stats


async def check_stabilization(
    session: AsyncSession, target_date: date, params: dict
) -> list[str]:
    """检测企稳信号，返回触发的 ts_code 列表。"""
    rows = (await session.execute(STABILIZATION_SQL, {
        "target_date": target_date,
        "min_days": params.get("min_washout_days", 3),
        "max_amp": params.get("max_tk_amplitude", 3.0),
        "max_vol_ratio": params.get("max_vol_shrink_ratio", 0.40),
        "ma_tolerance": params.get("ma_support_tolerance", 0.015),
    })).fetchall()

    if not rows:
        return []

    triggered_ids = [r.id for r in rows]
    triggered_codes = [r.ts_code for r in rows]

    await session.execute(text(
        "UPDATE strategy_watchpool SET status='triggered', triggered_date=:d, "
        "updated_at=:d WHERE id = ANY(:ids)"
    ), {"ids": triggered_ids, "d": target_date})

    logger.info("[watchpool] %d 只股票企稳触发: %s", len(triggered_codes), triggered_codes[:5])
    return triggered_codes


async def cleanup_old_entries(session: AsyncSession, keep_days: int = 30) -> int:
    """清理已终结的旧记录。"""
    r = await session.execute(text(
        "DELETE FROM strategy_watchpool WHERE status != 'watching' "
        "AND updated_at < NOW() - INTERVAL ':days days'"
    ), {"days": keep_days})
    return r.rowcount or 0
