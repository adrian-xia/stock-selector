"""复权因子批量更新。

Tushare adj_factor 接口返回除权除息日的累积前复权因子。
需要将每个除权日的因子填充到后续所有交易日，直到下一个除权日。

例如：
  除权日 2024-06-19, foreAdjustFactor=0.949509
  除权日 2024-12-20, foreAdjustFactor=0.964356
  → 2024-06-19 ~ 2024-12-19 的所有交易日 adj_factor = 0.949509
  → 2024-12-20 ~ 下一个除权日前 的所有交易日 adj_factor = 0.964356
"""

import logging
from datetime import date as date_type

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


def _to_date(val: str | date_type) -> date_type:
    """将字符串或 date 对象统一转为 date。"""
    if isinstance(val, date_type):
        return val
    return date_type.fromisoformat(str(val))


async def batch_update_adj_factor(
    session_factory: async_sessionmaker[AsyncSession],
    ts_code: str,
    records: list[dict],
) -> int:
    """按除权日区间填充 stock_daily.adj_factor。

    Args:
        session_factory: 异步数据库会话工厂
        ts_code: 股票代码
        records: Tushare 返回的除权日记录，按日期升序排列，
                 每个 dict 含 trade_date (str) 和 adj_factor (Decimal)

    Returns:
        更新的行数
    """
    if not records:
        return 0

    # 按日期升序排列
    sorted_records = sorted(records, key=lambda r: r["trade_date"])

    total_updated = 0

    async with session_factory() as session:
        for i, rec in enumerate(sorted_records):
            start_date = _to_date(rec["trade_date"])
            adj_factor = float(rec["adj_factor"])

            # 区间结束日期：下一个除权日的前一天，或无穷大
            if i + 1 < len(sorted_records):
                # 更新从当前除权日到下一个除权日前一天
                end_date = _to_date(sorted_records[i + 1]["trade_date"])
                stmt = text("""
                    UPDATE stock_daily
                    SET adj_factor = :adj_factor,
                        updated_at = NOW()
                    WHERE ts_code = :ts_code
                      AND trade_date >= :start_date
                      AND trade_date < :end_date
                """)
                result = await session.execute(stmt, {
                    "ts_code": ts_code,
                    "adj_factor": adj_factor,
                    "start_date": start_date,
                    "end_date": end_date,
                })
            else:
                # 最后一个除权日：更新到所有后续交易日
                stmt = text("""
                    UPDATE stock_daily
                    SET adj_factor = :adj_factor,
                        updated_at = NOW()
                    WHERE ts_code = :ts_code
                      AND trade_date >= :start_date
                """)
                result = await session.execute(stmt, {
                    "ts_code": ts_code,
                    "adj_factor": adj_factor,
                    "start_date": start_date,
                })

            total_updated += result.rowcount

        # 第一个除权日之前的交易日也需要填充（使用第一个因子）
        if sorted_records:
            first_date = _to_date(sorted_records[0]["trade_date"])
            first_factor = float(sorted_records[0]["adj_factor"])
            stmt = text("""
                UPDATE stock_daily
                SET adj_factor = :adj_factor,
                    updated_at = NOW()
                WHERE ts_code = :ts_code
                  AND trade_date < :first_date
                  AND adj_factor IS NULL
            """)
            result = await session.execute(stmt, {
                "ts_code": ts_code,
                "adj_factor": first_factor,
                "first_date": first_date,
            })
            total_updated += result.rowcount

        await session.commit()

    if total_updated > 0:
        logger.debug("更新 %s 复权因子: %d 行", ts_code, total_updated)

    return total_updated
