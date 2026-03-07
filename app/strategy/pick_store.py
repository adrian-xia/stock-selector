"""策略选股结果持久化。"""

import logging
from datetime import date
from typing import Protocol

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

logger = logging.getLogger(__name__)


class _PickLike(Protocol):
    ts_code: str
    close: float
    weighted_score: float

    @property
    def matched_strategies(self) -> list[str]:
        ...

    @property
    def ai_score(self) -> int | None:
        ...


async def save_strategy_picks(
    session_factory: async_sessionmaker,
    strategy_names: list[str],
    target_date: date,
    picks: list[_PickLike],
) -> int:
    """将选股结果批量写入 `strategy_picks` 表。"""
    if not picks or not strategy_names:
        return 0

    rows: list[dict] = []
    for pick in picks:
        for strategy_name in pick.matched_strategies:
            if strategy_name not in strategy_names:
                continue
            rows.append({
                "strategy_name": strategy_name,
                "pick_date": target_date,
                "ts_code": pick.ts_code,
                "pick_score": (
                    float(pick.ai_score)
                    if pick.ai_score is not None
                    else float(pick.weighted_score)
                ),
                "pick_close": pick.close if pick.close else None,
            })

    if not rows:
        return 0

    deduped: dict[tuple[str, str], dict] = {}
    for row in rows:
        deduped[(row["strategy_name"], row["ts_code"])] = row

    async with session_factory() as session:
        for row in deduped.values():
            await session.execute(
                text("""
                    INSERT INTO strategy_picks
                        (strategy_name, pick_date, ts_code, pick_score, pick_close)
                    VALUES
                        (:strategy_name, :pick_date, :ts_code, :pick_score, :pick_close)
                    ON CONFLICT ON CONSTRAINT uq_picks_strategy_date_code
                    DO UPDATE SET
                        pick_score = EXCLUDED.pick_score,
                        pick_close = EXCLUDED.pick_close,
                        updated_at = NOW()
                """),
                row,
            )
        await session.commit()

    logger.info("[strategy_picks] 写入 %d 条选股记录（日期：%s）", len(deduped), target_date)
    return len(deduped)
