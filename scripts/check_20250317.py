"""查看 2025-03-17 的数据详情。"""

import asyncio
import logging
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import async_session_factory
from app.logger import setup_logging
from sqlalchemy import text

setup_logging()
logger = logging.getLogger(__name__)


async def main():
    """主函数。"""
    target_date = date(2025, 3, 17)

    async with async_session_factory() as session:
        # 1. 检查交易日历
        result = await session.execute(
            text("SELECT is_open FROM trade_calendar WHERE cal_date = :date"),
            {"date": target_date}
        )
        is_open = result.scalar()
        logger.info(f"{target_date} 是否交易日：{is_open}")

        # 2. 查看这天的所有数据
        result = await session.execute(
            text("""
                SELECT ts_code, open, high, low, close, vol, amount
                FROM stock_daily
                WHERE trade_date = :date
                ORDER BY ts_code
            """),
            {"date": target_date}
        )
        rows = result.fetchall()

        logger.info(f"\n{target_date} 的日线数据（共 {len(rows)} 条）：")
        for row in rows:
            logger.info(f"  {row[0]}: open={row[1]}, high={row[2]}, low={row[3]}, close={row[4]}, vol={row[5]}, amount={row[6]}")

        # 3. 检查 raw 表
        result = await session.execute(
            text("SELECT COUNT(*) FROM raw_tushare_daily WHERE trade_date = :date"),
            {"date": target_date.strftime('%Y%m%d')}
        )
        raw_count = result.scalar()
        logger.info(f"\nraw_tushare_daily 表中的记录数：{raw_count}")

        if raw_count > 0:
            result = await session.execute(
                text("""
                    SELECT ts_code, open, high, low, close, vol, amount
                    FROM raw_tushare_daily
                    WHERE trade_date = :date
                    ORDER BY ts_code
                    LIMIT 10
                """),
                {"date": target_date.strftime('%Y%m%d')}
            )
            rows = result.fetchall()
            logger.info(f"\nraw_tushare_daily 前 10 条记录：")
            for row in rows:
                logger.info(f"  {row[0]}: open={row[1]}, high={row[2]}, low={row[3]}, close={row[4]}, vol={row[5]}, amount={row[6]}")

        # 4. 检查前后几天的数据量
        result = await session.execute(
            text("""
                SELECT trade_date, COUNT(*) as cnt
                FROM stock_daily
                WHERE trade_date BETWEEN :start AND :end
                GROUP BY trade_date
                ORDER BY trade_date
            """),
            {"start": date(2025, 3, 14), "end": date(2025, 3, 20)}
        )
        rows = result.fetchall()
        logger.info(f"\n前后几天的数据量对比：")
        for trade_date, cnt in rows:
            marker = " ⚠️" if cnt < 100 else ""
            logger.info(f"  {trade_date}：{cnt} 条{marker}")


if __name__ == "__main__":
    asyncio.run(main())
