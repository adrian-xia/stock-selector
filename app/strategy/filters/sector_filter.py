"""行业板块共振过滤器 — 基于 concept_daily 预计算数据。"""

import logging
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

STRONG_SECTORS_SQL = text("""
    WITH sector_perf AS (
        SELECT ts_code, SUM(pct_chg) AS total_chg
        FROM concept_daily
        WHERE trade_date BETWEEN :start_date AND :end_date
        GROUP BY ts_code
    ),
    ranked AS (
        SELECT ts_code, total_chg,
               PERCENT_RANK() OVER (ORDER BY total_chg DESC) AS pct_rank
        FROM sector_perf
    )
    SELECT ts_code FROM ranked WHERE pct_rank <= :top_pct
""")

TRADE_DATE_OFFSET_SQL = text("""
    SELECT trade_date FROM concept_daily
    WHERE trade_date <= :target_date
    GROUP BY trade_date
    ORDER BY trade_date DESC
    LIMIT 1 OFFSET :offset
""")


async def get_strong_sectors(
    session: AsyncSession,
    target_date: date,
    top_pct: float = 0.20,
    momentum_days: int = 5,
) -> set[str]:
    """获取排名前 top_pct 的强势板块代码集合。"""
    row = (await session.execute(
        TRADE_DATE_OFFSET_SQL, {"target_date": target_date, "offset": momentum_days}
    )).fetchone()
    if not row:
        return set()

    start_date = row.trade_date
    rows = await session.execute(STRONG_SECTORS_SQL, {
        "start_date": start_date, "end_date": target_date, "top_pct": top_pct,
    })
    return {r.ts_code for r in rows}
