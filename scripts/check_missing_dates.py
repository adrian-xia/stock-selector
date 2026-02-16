"""检查缺失的交易日数据。"""

import asyncio
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import async_session_factory
from app.logger import setup_logging
from sqlalchemy import text

setup_logging()
logger = logging.getLogger(__name__)


async def check_missing_dates(start_date: date, end_date: date):
    """检查缺失的交易日数据。"""
    logger.info(f"检查日期范围：{start_date} 到 {end_date}")

    async with async_session_factory() as session:
        # 1. 获取所有交易日
        result = await session.execute(
            text("""
                SELECT cal_date
                FROM trade_calendar
                WHERE cal_date BETWEEN :start AND :end
                  AND is_open = true
                ORDER BY cal_date
            """),
            {"start": start_date, "end": end_date}
        )
        trade_dates = [row[0] for row in result.fetchall()]
        logger.info(f"交易日总数：{len(trade_dates)}")

        # 2. 获取有日线数据的日期
        result = await session.execute(
            text("""
                SELECT DISTINCT trade_date
                FROM stock_daily
                WHERE trade_date BETWEEN :start AND :end
                ORDER BY trade_date
            """),
            {"start": start_date, "end": end_date}
        )
        daily_dates = [row[0] for row in result.fetchall()]
        logger.info(f"有日线数据的日期数：{len(daily_dates)}")

        # 3. 找出缺失的日期
        trade_dates_set = set(trade_dates)
        daily_dates_set = set(daily_dates)
        missing_dates = sorted(trade_dates_set - daily_dates_set)

        if missing_dates:
            logger.error(f"\n❌ 发现 {len(missing_dates)} 个交易日缺少日线数据：")
            for missing_date in missing_dates:
                # 检查这个日期有多少只股票的数据
                result = await session.execute(
                    text("SELECT COUNT(*) FROM stock_daily WHERE trade_date = :date"),
                    {"date": missing_date}
                )
                count = result.scalar()
                logger.error(f"  - {missing_date}：{count} 条记录")
        else:
            logger.info("\n✅ 所有交易日都有日线数据")

        # 4. 检查每个交易日的数据量
        logger.info("\n检查每个交易日的数据量...")
        result = await session.execute(
            text("""
                SELECT trade_date, COUNT(*) as cnt
                FROM stock_daily
                WHERE trade_date BETWEEN :start AND :end
                GROUP BY trade_date
                ORDER BY cnt ASC
                LIMIT 10
            """),
            {"start": start_date, "end": end_date}
        )
        low_count_dates = result.fetchall()

        if low_count_dates:
            logger.warning("\n数据量最少的 10 个交易日：")
            for trade_date, cnt in low_count_dates:
                logger.warning(f"  - {trade_date}：{cnt} 条记录")

        # 5. 检查技术指标
        result = await session.execute(
            text("""
                SELECT DISTINCT trade_date
                FROM technical_daily
                WHERE trade_date BETWEEN :start AND :end
                ORDER BY trade_date
            """),
            {"start": start_date, "end": end_date}
        )
        tech_dates = [row[0] for row in result.fetchall()]
        logger.info(f"\n有技术指标的日期数：{len(tech_dates)}")

        tech_dates_set = set(tech_dates)
        missing_tech_dates = sorted(trade_dates_set - tech_dates_set)

        if missing_tech_dates:
            logger.error(f"\n❌ 发现 {len(missing_tech_dates)} 个交易日缺少技术指标：")
            for missing_date in missing_tech_dates[:10]:  # 只显示前 10 个
                logger.error(f"  - {missing_date}")
            if len(missing_tech_dates) > 10:
                logger.error(f"  ... 还有 {len(missing_tech_dates) - 10} 个")
        else:
            logger.info("✅ 所有交易日都有技术指标")

        return len(missing_dates) == 0 and len(missing_tech_dates) == 0


async def main():
    """主函数。"""
    end_date = date.today()
    start_date = end_date - timedelta(days=365)

    logger.info("="*60)
    logger.info("检查缺失的交易日数据")
    logger.info("="*60)

    all_ok = await check_missing_dates(start_date, end_date)

    if all_ok:
        logger.info("\n🎉 数据完整性检查通过！")
        sys.exit(0)
    else:
        logger.error("\n❌ 发现数据缺失")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
