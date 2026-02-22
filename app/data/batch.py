"""批量日线数据同步模块（按日期模式）。

Tushare 支持按日期获取全市场数据，每个交易日只需 3 次 API 调用。
本模块提供按日期循环的批量同步功能。

使用示例：
    from app.data.batch import batch_sync_daily
    from app.database import async_session_factory

    result = await batch_sync_daily(
        session_factory=async_session_factory,
        trade_dates=[date(2026, 2, 10), date(2026, 2, 11)],
    )
"""

import logging
import time
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.data.manager import DataManager
from app.data.tushare import TushareClient

logger = logging.getLogger(__name__)

# 全量导入时需要管理索引的表
_FULL_IMPORT_TABLES = [
    "stock_daily",
    "technical_daily",
    "money_flow",
    "dragon_tiger",
    "index_daily",
    "index_weight",
    "index_technical_daily",
]


async def batch_sync_daily(
    session_factory: async_sessionmaker,
    trade_dates: list[date],
    manager: DataManager | None = None,
    full_import: bool = False,
) -> dict[str, Any]:
    """按日期批量同步全市场日线数据（sync_raw_daily + etl_daily）。

    Args:
        session_factory: 数据库会话工厂
        trade_dates: 交易日期列表
        manager: DataManager 实例（可选，传入则复用）
        full_import: 是否为全量导入模式（启用索引管理）

    Returns:
        dict 包含同步结果统计
    """
    start_time = time.monotonic()
    total = len(trade_dates)

    if manager is None:
        client = TushareClient()
        manager = DataManager(
            session_factory=session_factory,
            clients={"tushare": client},
            primary="tushare",
        )

    logger.info(
        "[批量同步] 开始：共 %d 个交易日%s",
        total,
        "（全量导入模式，启用索引管理）" if full_import else "",
    )

    if full_import:
        from app.data.index_mgmt import with_index_management
        from app.database import engine

        async with with_index_management(engine, _FULL_IMPORT_TABLES):
            return await _sync_loop(manager, trade_dates, start_time)
    else:
        return await _sync_loop(manager, trade_dates, start_time)


async def _sync_loop(
    manager: DataManager,
    trade_dates: list[date],
    start_time: float,
) -> dict[str, Any]:
    """执行逐日同步循环。"""
    total = len(trade_dates)
    success_count = 0
    failed_count = 0
    failed_dates: list[date] = []

    for idx, td in enumerate(trade_dates, 1):
        td_start = time.monotonic()
        try:
            # 1. 拉取原始数据到 raw 表
            raw_counts = await manager.sync_raw_daily(td)
            # 2. ETL 清洗到 stock_daily
            etl_result = await manager.etl_daily(td)

            td_elapsed = time.monotonic() - td_start
            logger.info(
                "[批量同步] %d/%d %s: raw=%s, etl=%d, 耗时 %.1fs",
                idx, total, td, raw_counts, etl_result["inserted"], td_elapsed,
            )
            success_count += 1
        except Exception as e:
            td_elapsed = time.monotonic() - td_start
            logger.warning(
                "[批量同步] %d/%d %s 失败 (%.1fs): %s",
                idx, total, td, td_elapsed, e,
            )
            failed_count += 1
            failed_dates.append(td)

    elapsed = time.monotonic() - start_time
    avg_time = elapsed / total if total > 0 else 0
    logger.info(
        "[批量同步] 完成：成功 %d 天，失败 %d 天，总耗时 %.1fs，平均 %.1fs/天",
        success_count, failed_count, elapsed, avg_time,
    )

    return {
        "success": success_count,
        "failed": failed_count,
        "failed_dates": failed_dates,
        "elapsed_seconds": round(elapsed, 1),
    }
