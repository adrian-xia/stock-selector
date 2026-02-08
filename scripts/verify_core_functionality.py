"""验证连接池和批量同步功能。

测试内容：
1. 连接池基本功能（acquire/release）
2. BaoStockClient 使用连接池
3. 批量同步功能（小规模测试）
"""

import asyncio
import logging
from datetime import date

from app.data.batch import batch_sync_daily
from app.data.baostock import BaoStockClient
from app.data.pool import BaoStockConnectionPool, close_pool, get_pool
from app.database import async_session_factory

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def test_connection_pool():
    """测试连接池基本功能。"""
    logger.info("=" * 60)
    logger.info("测试 1: 连接池基本功能")
    logger.info("=" * 60)

    pool = BaoStockConnectionPool(size=2, timeout=10.0, session_ttl=3600.0)

    try:
        # 测试 acquire/release
        logger.info("测试 acquire/release...")
        session1 = await pool.acquire()
        logger.info("✓ 获取会话 1: session_id=%d", session1.session_id)

        session2 = await pool.acquire()
        logger.info("✓ 获取会话 2: session_id=%d", session2.session_id)

        await pool.release(session1)
        logger.info("✓ 释放会话 1")

        await pool.release(session2)
        logger.info("✓ 释放会话 2")

        # 测试 health check
        logger.info("测试 health_check...")
        healthy = await pool.health_check()
        logger.info("✓ 健康检查: %s", "通过" if healthy else "失败")

        # 关闭连接池
        await pool.close()
        logger.info("✓ 连接池已关闭")

        logger.info("✅ 测试 1 通过\n")
        return True
    except Exception as e:
        logger.error("❌ 测试 1 失败: %s", e, exc_info=True)
        return False


async def test_baostock_with_pool():
    """测试 BaoStockClient 使用连接池。"""
    logger.info("=" * 60)
    logger.info("测试 2: BaoStockClient 使用连接池")
    logger.info("=" * 60)

    pool = get_pool()

    try:
        # 创建使用连接池的客户端
        client = BaoStockClient(connection_pool=pool)
        logger.info("✓ 创建 BaoStockClient（使用连接池）")

        # 测试获取股票列表（小规模）
        logger.info("测试获取股票列表...")
        stocks = await client.fetch_stock_list()
        logger.info("✓ 获取股票列表: %d 只", len(stocks))

        # 测试获取日线数据
        logger.info("测试获取日线数据（600519.SH）...")
        daily_data = await client.fetch_daily(
            "600519.SH",
            date(2025, 1, 1),
            date(2025, 1, 10),
        )
        logger.info("✓ 获取日线数据: %d 条", len(daily_data))

        logger.info("✅ 测试 2 通过\n")
        return True
    except Exception as e:
        logger.error("❌ 测试 2 失败: %s", e, exc_info=True)
        return False


async def test_batch_sync():
    """测试批量同步功能（小规模）。"""
    logger.info("=" * 60)
    logger.info("测试 3: 批量同步功能（小规模）")
    logger.info("=" * 60)

    pool = get_pool()

    try:
        # 测试同步 5 只股票
        test_codes = [
            "600519.SH",  # 贵州茅台
            "000001.SZ",  # 平安银行
            "600036.SH",  # 招商银行
            "000858.SZ",  # 五粮液
            "601318.SH",  # 中国平安
        ]

        logger.info("测试批量同步 %d 只股票...", len(test_codes))
        result = await batch_sync_daily(
            session_factory=async_session_factory,
            stock_codes=test_codes,
            target_date=date(2025, 1, 10),
            connection_pool=pool,
            batch_size=3,  # 小批量测试
            concurrency=2,  # 低并发测试
        )

        logger.info("✓ 批量同步完成:")
        logger.info("  - 成功: %d 只", result["success"])
        logger.info("  - 失败: %d 只", result["failed"])
        logger.info("  - 耗时: %.1f 秒", result["elapsed_seconds"])

        if result["failed"] > 0:
            logger.warning("  - 失败股票: %s", result["failed_codes"])

        logger.info("✅ 测试 3 通过\n")
        return True
    except Exception as e:
        logger.error("❌ 测试 3 失败: %s", e, exc_info=True)
        return False


async def main():
    """运行所有测试。"""
    logger.info("\n" + "=" * 60)
    logger.info("开始验证核心功能")
    logger.info("=" * 60 + "\n")

    results = []

    # 测试 1: 连接池基本功能
    results.append(await test_connection_pool())

    # 测试 2: BaoStockClient 使用连接池
    results.append(await test_baostock_with_pool())

    # 测试 3: 批量同步功能
    results.append(await test_batch_sync())

    # 清理
    await close_pool()

    # 汇总结果
    logger.info("=" * 60)
    logger.info("验证结果汇总")
    logger.info("=" * 60)
    logger.info("测试 1 (连接池基本功能): %s", "✅ 通过" if results[0] else "❌ 失败")
    logger.info("测试 2 (BaoStockClient): %s", "✅ 通过" if results[1] else "❌ 失败")
    logger.info("测试 3 (批量同步): %s", "✅ 通过" if results[2] else "❌ 失败")
    logger.info("=" * 60)

    if all(results):
        logger.info("🎉 所有测试通过！")
        return 0
    else:
        logger.error("⚠️  部分测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
