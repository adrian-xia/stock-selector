"""批量日线数据同步模块。

提供批量并发同步功能，显著提升日线数据同步性能。

主要功能：
- batch_sync_daily(): 批量同步多只股票的日线数据
- 支持分批处理和并发控制
- 详细的进度日志和错误处理
- 单只股票失败不阻断整体同步

使用示例：
    from app.data.batch import batch_sync_daily
    from app.data.pool import get_pool
    from app.database import async_session_factory

    pool = get_pool()
    result = await batch_sync_daily(
        session_factory=async_session_factory,
        stock_codes=["600519.SH", "000001.SZ", ...],
        target_date=date(2025, 1, 1),
        connection_pool=pool,
    )
    print(f"成功: {result['success']}, 失败: {result['failed']}")
"""

import asyncio
import logging
import time
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import settings
from app.data.baostock import BaoStockClient
from app.data.manager import DataManager
from app.data.pool import BaoStockConnectionPool

logger = logging.getLogger(__name__)


async def batch_sync_daily(
    session_factory: async_sessionmaker,
    stock_codes: list[str],
    target_date: date,
    connection_pool: BaoStockConnectionPool | None = None,
    batch_size: int | None = None,
    concurrency: int | None = None,
) -> dict[str, Any]:
    """批量同步多只股票的日线数据。

    Args:
        session_factory: 数据库会话工厂
        stock_codes: 股票代码列表
        target_date: 目标日期
        connection_pool: BaoStock 连接池（可选）
        batch_size: 每批股票数（默认从配置读取）
        concurrency: 并发数（默认从配置读取）

    Returns:
        dict 包含同步结果统计：
        - success: 成功数
        - failed: 失败数
        - failed_codes: 失败的股票代码列表
        - elapsed_seconds: 耗时（秒）
    """
    batch_size = batch_size or settings.daily_sync_batch_size
    concurrency = concurrency or settings.daily_sync_concurrency

    start_time = time.monotonic()
    total = len(stock_codes)
    success_count = 0
    failed_count = 0
    failed_codes: list[str] = []

    logger.info(
        "[批量同步] 开始：%s，共 %d 只股票，批量大小=%d，并发数=%d",
        target_date, total, batch_size, concurrency,
    )

    # 创建 DataManager（使用连接池）
    client = BaoStockClient(connection_pool=connection_pool)
    manager = DataManager(
        session_factory=session_factory,
        clients={"baostock": client},
        primary="baostock",
    )

    # 分批处理
    batches = [
        stock_codes[i:i + batch_size]
        for i in range(0, total, batch_size)
    ]
    total_batches = len(batches)

    # 并发控制
    semaphore = asyncio.Semaphore(concurrency)

    async def sync_one(code: str) -> tuple[str, bool, float, str]:
        """同步单只股票，返回 (code, success, elapsed, error_msg)。"""
        async with semaphore:
            stock_start = time.monotonic()
            try:
                await manager.sync_daily(code, target_date, target_date)
                elapsed = time.monotonic() - stock_start

                # 检测慢速股票（>5秒）
                if elapsed > 5.0:
                    logger.warning("[批量同步] 慢速股票：%s 耗时 %.1fs", code, elapsed)

                return (code, True, elapsed, "")
            except Exception as e:
                elapsed = time.monotonic() - stock_start
                error_msg = str(e)
                logger.warning("[批量同步] 失败：%s - %s", code, error_msg)
                return (code, False, elapsed, error_msg)

    # 逐批执行
    for batch_idx, batch in enumerate(batches, 1):
        batch_start = time.monotonic()

        # 批内并发执行
        results = await asyncio.gather(*[sync_one(code) for code in batch])

        # 统计结果
        batch_success = sum(1 for _, success, _, _ in results if success)
        batch_failed = len(batch) - batch_success
        success_count += batch_success
        failed_count += batch_failed

        # 记录失败的股票
        for code, success, _, _ in results:
            if not success:
                failed_codes.append(code)

        batch_elapsed = time.monotonic() - batch_start
        logger.info(
            "[批量同步] Batch %d/%d 完成：成功 %d/%d，耗时 %.1fs",
            batch_idx, total_batches, batch_success, len(batch), batch_elapsed,
        )

    elapsed = time.monotonic() - start_time
    avg_time = elapsed / total if total > 0 else 0
    logger.info(
        "[批量同步] 完成：成功 %d 只，失败 %d 只，总耗时 %.1fs，平均 %.3fs/只",
        success_count, failed_count, elapsed, avg_time,
    )

    return {
        "success": success_count,
        "failed": failed_count,
        "failed_codes": failed_codes,
        "elapsed_seconds": round(elapsed, 1),
    }
