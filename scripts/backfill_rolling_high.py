"""回填 technical_daily 表中的 high_20/high_60 字段。

使用 PostgreSQL 窗口函数直接在数据库中计算，比逐股 Python 计算快 100x+。
"""

import asyncio
import logging
import time

from sqlalchemy import text

from app.database import async_session_factory

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def backfill_rolling_high() -> None:
    """使用窗口函数批量回填 high_20 和 high_60。"""
    start = time.time()

    async with async_session_factory() as session:
        # 统计当前 NULL 行数
        result = await session.execute(text(
            "SELECT COUNT(*) FROM technical_daily WHERE high_20 IS NULL OR high_60 IS NULL"
        ))
        null_count = result.scalar()
        logger.info("待回填行数：%d", null_count)

        if null_count == 0:
            logger.info("无需回填，所有行已有 high_20/high_60 数据")
            return

        # 使用窗口函数批量计算并更新
        # 注意：需要 JOIN stock_daily 获取 high 列
        logger.info("开始计算 high_20/high_60（窗口函数）...")

        await session.execute(text("""
            UPDATE technical_daily td
            SET
                high_20 = sub.high_20,
                high_60 = sub.high_60
            FROM (
                SELECT
                    ts_code,
                    trade_date,
                    MAX(high) OVER (
                        PARTITION BY ts_code
                        ORDER BY trade_date
                        ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                    ) AS high_20,
                    MAX(high) OVER (
                        PARTITION BY ts_code
                        ORDER BY trade_date
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                    ) AS high_60
                FROM stock_daily
            ) sub
            WHERE td.ts_code = sub.ts_code
              AND td.trade_date = sub.trade_date
              AND (td.high_20 IS NULL OR td.high_60 IS NULL)
        """))

        await session.commit()

        # 验证结果
        result = await session.execute(text(
            "SELECT COUNT(*) FROM technical_daily WHERE high_20 IS NULL OR high_60 IS NULL"
        ))
        remaining = result.scalar()

        elapsed = round(time.time() - start, 1)
        logger.info(
            "回填完成：耗时 %.1fs，剩余 NULL 行 %d（新股数据不足窗口期为正常）",
            elapsed, remaining,
        )

        # 抽样验证
        sample = await session.execute(text("""
            SELECT td.ts_code, td.trade_date, td.high_20, td.high_60
            FROM technical_daily td
            WHERE td.high_20 IS NOT NULL
            ORDER BY td.trade_date DESC
            LIMIT 5
        """))
        logger.info("抽样数据：")
        for row in sample.fetchall():
            logger.info("  %s %s  high_20=%.2f  high_60=%.2f", row[0], row[1], row[2], row[3])


if __name__ == "__main__":
    asyncio.run(backfill_rolling_high())
