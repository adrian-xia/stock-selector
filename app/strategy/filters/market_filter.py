"""大盘环境过滤器 — 基于 index_technical_daily 预计算指标。"""

import logging
from datetime import date
from enum import Enum

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class MarketState(str, Enum):
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"


EVALUATE_SQL = text("""
    SELECT id.close, itd.ma20, itd.ma60, itd.macd_dif
    FROM index_daily id
    JOIN index_technical_daily itd
      ON id.ts_code = itd.ts_code AND id.trade_date = itd.trade_date
    WHERE id.ts_code = :index_code AND id.trade_date = :target_date
""")


async def evaluate_market(
    session: AsyncSession, target_date: date, index_code: str = "000300.SH"
) -> MarketState:
    """评估大盘环境，返回 bullish/neutral/bearish。"""
    row = (await session.execute(EVALUATE_SQL, {
        "index_code": index_code, "target_date": target_date,
    })).fetchone()

    if not row:
        return MarketState.NEUTRAL

    close = float(row.close or 0)
    ma20 = float(row.ma20 or 0)
    ma60 = float(row.ma60 or 0)
    macd = float(row.macd_dif or 0)

    if ma20 > 0 and close > ma20 and macd > 0:
        return MarketState.BULLISH
    elif ma60 > 0 and close > ma60:
        return MarketState.NEUTRAL
    else:
        return MarketState.BEARISH
