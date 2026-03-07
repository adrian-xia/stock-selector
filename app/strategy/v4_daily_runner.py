"""V4 量价配合策略日常执行器。

将独立 V4 `volume-price-pattern` 纳入日常选股落库流程：
1. 读取 strategies 表中的启用状态和自定义参数
2. 执行观察池状态机
3. 将命中结果标准化为通用 StockPick
4. 写入 strategy_picks，供 StarMap 统一消费
"""

from __future__ import annotations

import json
import logging
from datetime import date

import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.database import async_session_factory
from app.strategy.pick_store import save_strategy_picks
from app.strategy.pick_types import StockPick
from app.strategy.technical.volume_price_pattern import VolumePricePatternStrategy

logger = logging.getLogger(__name__)

V4_STRATEGY_NAME = "volume-price-pattern"


async def _load_strategy_config(session: AsyncSession) -> tuple[bool, dict]:
    """读取 V4 策略的启用状态与参数。"""
    result = await session.execute(
        text(
            "SELECT is_enabled, params FROM strategies WHERE name = :name LIMIT 1"
        ),
        {"name": V4_STRATEGY_NAME},
    )
    row = result.first()
    if not row:
        return True, {}

    enabled = bool(row[0])
    raw_params = row[1]
    if isinstance(raw_params, str):
        try:
            raw_params = json.loads(raw_params)
        except json.JSONDecodeError:
            raw_params = {}
    return enabled, raw_params or {}


async def _fetch_daily_snapshot(
    session: AsyncSession,
    target_date: date,
) -> pd.DataFrame:
    """获取 V4 日常执行所需的快照数据。"""
    result = await session.execute(
        text(
            """
            SELECT
                sd.ts_code,
                s.name,
                sd.open,
                sd.high,
                sd.low,
                sd.close,
                sd.vol,
                sd.pct_chg,
                COALESCE(td.vol_ratio, 0) AS vol_ratio
            FROM stock_daily sd
            JOIN stocks s
              ON sd.ts_code = s.ts_code
            LEFT JOIN technical_daily td
              ON sd.ts_code = td.ts_code
             AND sd.trade_date = td.trade_date
            WHERE sd.trade_date = :trade_date
              AND sd.vol > 0
              AND s.list_status = 'L'
            ORDER BY sd.ts_code
            """
        ),
        {"trade_date": target_date},
    )
    rows = result.fetchall()
    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(
        rows,
        columns=[
            "ts_code",
            "name",
            "open",
            "high",
            "low",
            "close",
            "vol",
            "pct_chg",
            "vol_ratio",
        ],
    )


async def _load_triggered_meta(
    session: AsyncSession,
    target_date: date,
) -> dict[str, dict]:
    """读取 V4 当日触发后的观察池元信息。"""
    result = await session.execute(
        text(
            """
            SELECT ts_code, washout_days, sector_score
            FROM strategy_watchpool
            WHERE strategy_name = :strategy_name
              AND status = 'triggered'
              AND triggered_date = :trade_date
            """
        ),
        {"strategy_name": V4_STRATEGY_NAME, "trade_date": target_date},
    )
    return {
        row[0]: {
            "washout_days": int(row[1] or 0),
            "sector_score": float(row[2] or 0.0),
        }
        for row in result.fetchall()
    }


def _build_weighted_score(meta: dict) -> float:
    """构造 V4 写入 strategy_picks 的统一评分口径。"""
    sector_score = float(meta.get("sector_score") or 0.0)
    washout_days = int(meta.get("washout_days") or 0)

    base_score = 78.0
    sector_bonus = sector_score * 6.0
    washout_bonus = max(0.0, 3.0 - max(washout_days - 3, 0) * 0.5)
    return round(base_score + sector_bonus + washout_bonus, 4)


async def execute_volume_price_pattern_daily(
    target_date: date,
    session_factory: async_sessionmaker = async_session_factory,
    save_picks: bool = True,
) -> list[StockPick]:
    """执行 V4 量价配合策略并写入 strategy_picks。"""
    logger.info("[V4 Daily] 开始执行：%s", target_date)

    async with session_factory() as session:
        enabled, params = await _load_strategy_config(session)
        if not enabled:
            logger.info("[V4 Daily] 策略已禁用，跳过")
            return []

        snapshot_df = await _fetch_daily_snapshot(session, target_date)
        if snapshot_df.empty:
            logger.warning("[V4 Daily] 当日无可用行情数据")
            return []

    strategy = VolumePricePatternStrategy(params=params)
    mask = await strategy.filter_batch(snapshot_df, target_date)
    triggered_df = snapshot_df.loc[mask].copy()

    if triggered_df.empty:
        logger.info("[V4 Daily] 当日无触发结果")
        return []

    async with session_factory() as session:
        meta_map = await _load_triggered_meta(session, target_date)

    picks: list[StockPick] = []
    for _, row in triggered_df.iterrows():
        ts_code = row["ts_code"]
        weighted_score = _build_weighted_score(meta_map.get(ts_code, {}))
        picks.append(
            StockPick(
                ts_code=ts_code,
                name=str(row["name"] or ts_code),
                close=float(row["close"] or 0.0),
                pct_chg=float(row["pct_chg"] or 0.0),
                matched_strategies=[V4_STRATEGY_NAME],
                match_count=1,
                weighted_score=weighted_score,
            )
        )

    picks.sort(key=lambda item: item.weighted_score, reverse=True)

    if save_picks:
        await save_strategy_picks(
            session_factory=session_factory,
            strategy_names=[V4_STRATEGY_NAME],
            target_date=target_date,
            picks=picks,
        )

    logger.info("[V4 Daily] 完成：触发 %d 只", len(picks))
    return picks
