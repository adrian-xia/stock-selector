"""重新同步 2025-03-17 的数据。"""

import asyncio
import logging
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.data.manager import DataManager
from app.data.tushare import TushareClient
from app.database import async_session_factory
from app.logger import setup_logging
from sqlalchemy import text

setup_logging()
logger = logging.getLogger(__name__)


async def main():
    """主函数。"""
    target_date = date(2025, 3, 17)

    logger.info("="*60)
    logger.info(f"重新同步 {target_date} 的数据")
    logger.info("="*60)

    # 1. 检查当前状态
    async with async_session_factory() as session:
        result = await session.execute(
            text("SELECT COUNT(*) FROM stock_daily WHERE trade_date = :date"),
            {"date": target_date}
        )
        before_count = result.scalar()
        logger.info(f"当前 stock_daily 记录数：{before_count}")

        result = await session.execute(
            text("SELECT COUNT(*) FROM raw_tushare_daily WHERE trade_date = :date"),
            {"date": target_date.strftime('%Y%m%d')}
        )
        raw_count = result.scalar()
        logger.info(f"当前 raw_tushare_daily 记录数：{raw_count}")

    # 2. 初始化 DataManager
    logger.info("\n初始化 DataManager...")
    tushare_client = TushareClient(
        token=settings.tushare_token,
        retry_count=settings.tushare_retry_count,
        retry_interval=settings.tushare_retry_interval,
        qps_limit=settings.tushare_qps_limit,
    )
    manager = DataManager(
        session_factory=async_session_factory,
        clients={"tushare": tushare_client},
        primary="tushare",
    )

    # 3. 删除旧数据
    logger.info(f"\n删除 {target_date} 的旧数据...")
    async with async_session_factory() as session:
        # 删除 stock_daily
        result = await session.execute(
            text("DELETE FROM stock_daily WHERE trade_date = :date"),
            {"date": target_date}
        )
        await session.commit()
        logger.info(f"  - 删除 stock_daily：{result.rowcount} 条")

        # 删除 technical_daily
        result = await session.execute(
            text("DELETE FROM technical_daily WHERE trade_date = :date"),
            {"date": target_date}
        )
        await session.commit()
        logger.info(f"  - 删除 technical_daily：{result.rowcount} 条")

        # 删除 raw 表数据
        result = await session.execute(
            text("DELETE FROM raw_tushare_daily WHERE trade_date = :date"),
            {"date": target_date.strftime('%Y%m%d')}
        )
        await session.commit()
        logger.info(f"  - 删除 raw_tushare_daily：{result.rowcount} 条")

        result = await session.execute(
            text("DELETE FROM raw_tushare_adj_factor WHERE trade_date = :date"),
            {"date": target_date.strftime('%Y%m%d')}
        )
        await session.commit()
        logger.info(f"  - 删除 raw_tushare_adj_factor：{result.rowcount} 条")

        result = await session.execute(
            text("DELETE FROM raw_tushare_daily_basic WHERE trade_date = :date"),
            {"date": target_date.strftime('%Y%m%d')}
        )
        await session.commit()
        logger.info(f"  - 删除 raw_tushare_daily_basic：{result.rowcount} 条")

    # 4. 重新同步原始数据
    logger.info(f"\n重新同步 {target_date} 的原始数据...")
    try:
        result = await manager.sync_raw_daily(target_date)
        logger.info(f"  - daily: {result['daily']} 条")
        logger.info(f"  - adj_factor: {result['adj_factor']} 条")
        logger.info(f"  - daily_basic: {result['daily_basic']} 条")
    except Exception as e:
        logger.error(f"❌ 同步原始数据失败：{e}", exc_info=True)
        sys.exit(1)

    # 5. ETL 清洗
    logger.info(f"\nETL 清洗 {target_date} 的数据...")
    try:
        result = await manager.etl_daily(target_date)
        logger.info(f"  - 写入 stock_daily：{result['inserted']} 条")
    except Exception as e:
        logger.error(f"❌ ETL 清洗失败：{e}", exc_info=True)
        sys.exit(1)

    # 6. 计算技术指标
    logger.info(f"\n计算 {target_date} 的技术指标...")
    try:
        from app.data.indicator import compute_incremental

        result = await compute_incremental(
            session_factory=async_session_factory,
            target_date=target_date,
        )
        logger.info(f"  - 计算技术指标：成功 {result['success']} 只，失败 {result['failed']} 只")
    except Exception as e:
        logger.error(f"❌ 计算技术指标失败：{e}", exc_info=True)
        sys.exit(1)

    # 7. 验证结果
    logger.info(f"\n验证 {target_date} 的数据...")
    async with async_session_factory() as session:
        result = await session.execute(
            text("SELECT COUNT(*) FROM stock_daily WHERE trade_date = :date"),
            {"date": target_date}
        )
        after_count = result.scalar()
        logger.info(f"  - stock_daily 记录数：{after_count}")

        result = await session.execute(
            text("SELECT COUNT(*) FROM technical_daily WHERE trade_date = :date"),
            {"date": target_date}
        )
        tech_count = result.scalar()
        logger.info(f"  - technical_daily 记录数：{tech_count}")

        result = await session.execute(
            text("SELECT COUNT(*) FROM raw_tushare_daily WHERE trade_date = :date"),
            {"date": target_date.strftime('%Y%m%d')}
        )
        raw_count = result.scalar()
        logger.info(f"  - raw_tushare_daily 记录数：{raw_count}")

    if after_count > 1000:  # 至少应该有 1000 条记录
        logger.info(f"\n✅ 数据同步成功！")
        sys.exit(0)
    else:
        logger.error(f"\n❌ 数据同步失败，记录数过少：{after_count}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
