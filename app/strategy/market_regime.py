"""V2 策略引擎的市场状态读取与缓存。"""

from __future__ import annotations

import logging
from datetime import date
from enum import Enum

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.cache.redis_client import get_redis

logger = logging.getLogger(__name__)

_REDIS_KEY_PREFIX = "market:regime"
_REDIS_TTL_SECONDS = 7 * 24 * 60 * 60
_BENCHMARK_CODE = "000001.SH"


class MarketRegime(str, Enum):
    """市场状态枚举。"""

    BULL = "bull"
    RANGE = "range"
    BEAR = "bear"


def _redis_key(target_date: date) -> str:
    return f"{_REDIS_KEY_PREFIX}:{target_date.isoformat()}"


def _normalize_regime(value: str | bytes | None) -> MarketRegime | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="ignore")
    try:
        return MarketRegime(value)
    except ValueError:
        return None


def _classify_regime(
    close: float | None,
    ma20: float | None,
    ma60: float | None,
    prev_ma20: float | None,
) -> MarketRegime:
    if close is None or ma20 is None or ma60 is None:
        return MarketRegime.RANGE

    ma20_slope_up = prev_ma20 is not None and ma20 > prev_ma20
    ma20_slope_down = prev_ma20 is not None and ma20 < prev_ma20

    if close > ma20 > ma60 and ma20_slope_up:
        return MarketRegime.BULL
    if close < ma20 < ma60 and ma20_slope_down:
        return MarketRegime.BEAR
    return MarketRegime.RANGE


async def _cache_regime(target_date: date, regime: MarketRegime) -> None:
    redis = get_redis()
    if redis is None:
        return
    try:
        await redis.set(
            _redis_key(target_date),
            regime.value,
            ex=_REDIS_TTL_SECONDS,
        )
    except Exception:
        logger.warning("[MarketRegime] Redis 写入失败", exc_info=True)


async def _load_regime_from_db(
    session_factory: async_sessionmaker[AsyncSession],
    target_date: date,
) -> MarketRegime | None:
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                SELECT regime
                FROM market_regime_daily
                WHERE trade_date = :target_date
                """
            ),
            {"target_date": target_date},
        )
        row = result.first()

    regime = _normalize_regime(row.regime if row else None)
    if regime is not None:
        await _cache_regime(target_date, regime)
    return regime


async def compute_and_store_regime(
    session_factory: async_sessionmaker[AsyncSession],
    target_date: date,
) -> MarketRegime:
    """计算并持久化当日市场状态。"""
    async with session_factory() as session:
        prev_result = await session.execute(
            text(
                """
                SELECT MAX(trade_date)
                FROM index_daily
                WHERE ts_code = :benchmark_code
                  AND trade_date < :target_date
                """
            ),
            {"target_date": target_date, "benchmark_code": _BENCHMARK_CODE},
        )
        prev_date = prev_result.scalar()

        row = await session.execute(
            text(
                """
                SELECT
                    i.close,
                    t.ma20,
                    t.ma60
                FROM index_daily i
                JOIN technical_daily t
                  ON i.ts_code = t.ts_code
                 AND i.trade_date = t.trade_date
                WHERE i.ts_code = :benchmark_code
                  AND i.trade_date = :target_date
                """
            ),
            {"target_date": target_date, "benchmark_code": _BENCHMARK_CODE},
        )
        current = row.first()

        prev_ma20 = None
        if prev_date is not None:
            prev_row = await session.execute(
                text(
                    """
                    SELECT ma20
                    FROM technical_daily
                    WHERE ts_code = :benchmark_code
                      AND trade_date = :prev_date
                    """
                ),
                {"prev_date": prev_date, "benchmark_code": _BENCHMARK_CODE},
            )
            prev = prev_row.first()
            prev_ma20 = float(prev.ma20) if prev and prev.ma20 is not None else None

        close = float(current.close) if current and current.close is not None else None
        ma20 = float(current.ma20) if current and current.ma20 is not None else None
        ma60 = float(current.ma60) if current and current.ma60 is not None else None
        regime = _classify_regime(close, ma20, ma60, prev_ma20)

        await session.execute(
            text(
                """
                INSERT INTO market_regime_daily (
                    trade_date, benchmark_code, regime, close, ma20, ma60, prev_ma20
                ) VALUES (
                    :trade_date, :benchmark_code, :regime, :close, :ma20, :ma60, :prev_ma20
                )
                ON CONFLICT (trade_date) DO UPDATE SET
                    benchmark_code = EXCLUDED.benchmark_code,
                    regime = EXCLUDED.regime,
                    close = EXCLUDED.close,
                    ma20 = EXCLUDED.ma20,
                    ma60 = EXCLUDED.ma60,
                    prev_ma20 = EXCLUDED.prev_ma20,
                    updated_at = NOW()
                """
            ),
            {
                "trade_date": target_date,
                "benchmark_code": _BENCHMARK_CODE,
                "regime": regime.value,
                "close": close,
                "ma20": ma20,
                "ma60": ma60,
                "prev_ma20": prev_ma20,
            },
        )
        await session.commit()

    await _cache_regime(target_date, regime)

    logger.info("[MarketRegime] %s -> %s", target_date, regime.value)
    return regime


async def get_market_regime(
    session_factory: async_sessionmaker[AsyncSession],
    target_date: date,
) -> MarketRegime:
    """读取市场状态：Redis → DB 持久化表 → 实时计算。"""
    redis = get_redis()
    if redis is not None:
        try:
            cached = await redis.get(_redis_key(target_date))
            regime = _normalize_regime(cached)
            if regime is not None:
                return regime
        except Exception:
            logger.warning("[MarketRegime] Redis 读取失败，回退计算", exc_info=True)

    persisted = await _load_regime_from_db(session_factory, target_date)
    if persisted is not None:
        return persisted

    return await compute_and_store_regime(session_factory, target_date)
