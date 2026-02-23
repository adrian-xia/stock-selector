"""调度器核心：创建、配置、启动和停止 APScheduler。"""

import logging
import time
from datetime import date, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings

logger = logging.getLogger(__name__)

# 模块级调度器实例
_scheduler: AsyncIOScheduler | None = None


def create_scheduler() -> AsyncIOScheduler:
    """创建并配置 APScheduler 实例。

    配置：
    - MemoryJobStore（内存存储，重启后自动重新注册）
    - timezone=Asia/Shanghai（A 股时区）
    - coalesce=True（错过多次触发时合并为一次）
    - max_instances=1（同一任务最多同时运行 1 个）
    - misfire_grace_time=300（错过触发后 5 分钟内仍可执行）
    """
    scheduler = AsyncIOScheduler(
        timezone="Asia/Shanghai",
        job_defaults={
            "coalesce": True,
            "max_instances": 1,
            "misfire_grace_time": 300,
        },
    )
    return scheduler


def register_jobs(scheduler: AsyncIOScheduler) -> None:
    """注册所有 cron 任务到调度器。

    Args:
        scheduler: APScheduler 实例
    """
    from app.scheduler.auto_update import auto_update_job
    from app.scheduler.jobs import retry_failed_stocks_job, sync_stock_list_job

    # 自动数据更新任务：默认周一至周五 15:30（替换原有盘后链路任务）
    if settings.auto_update_enabled:
        auto_update_cron = settings.scheduler_auto_update_cron
        parts = auto_update_cron.split()
        scheduler.add_job(
            func=auto_update_job,
            trigger=CronTrigger(
                minute=parts[0],
                hour=parts[1],
                day=parts[2],
                month=parts[3],
                day_of_week=parts[4],
                timezone="Asia/Shanghai",
            ),
            id="auto_data_update",
            name="自动数据更新",
            replace_existing=True,
        )
        logger.info("注册任务：自动数据更新 [%s]", auto_update_cron)
    else:
        logger.info("自动数据更新已禁用（AUTO_UPDATE_ENABLED=false）")

    # 失败重试任务：默认周一至周五 20:00
    retry_cron = settings.sync_failure_retry_cron
    parts = retry_cron.split()
    scheduler.add_job(
        func=retry_failed_stocks_job,
        trigger=CronTrigger(
            minute=parts[0],
            hour=parts[1],
            day=parts[2],
            month=parts[3],
            day_of_week=parts[4],
            timezone="Asia/Shanghai",
        ),
        id="retry_failed_stocks",
        name="失败股票重试",
        replace_existing=True,
    )
    logger.info("注册任务：失败股票重试 [%s]", retry_cron)

    # 周末股票列表同步：默认周六 08:00
    stock_sync_cron = settings.scheduler_stock_sync_cron
    parts = stock_sync_cron.split()
    scheduler.add_job(
        func=sync_stock_list_job,
        trigger=CronTrigger(
            minute=parts[0],
            hour=parts[1],
            day=parts[2],
            month=parts[3],
            day_of_week=parts[4],
            timezone="Asia/Shanghai",
        ),
        id="stock_list_sync",
        name="股票列表同步",
        replace_existing=True,
    )
    logger.info("注册任务：股票列表同步 [%s]", stock_sync_cron)


async def sync_stock_list_on_startup() -> None:
    """启动时更新股票列表（可配置跳过）。"""
    if not settings.sync_stock_list_on_startup:
        logger.info("[启动] 跳过股票列表更新（SYNC_STOCK_LIST_ON_STARTUP=false）")
        return

    start = time.monotonic()
    try:
        from app.data.manager import DataManager
        from app.data.tushare import TushareClient
        from app.database import async_session_factory

        client = TushareClient()
        manager = DataManager(
            session_factory=async_session_factory,
            clients={"tushare": client},
            primary="tushare",
        )
        result = await manager.sync_stock_list()
        elapsed = time.monotonic() - start
        logger.info("[启动] 股票列表更新完成：%s，耗时 %.1fs", result, elapsed)
    except Exception as e:
        elapsed = time.monotonic() - start
        logger.warning("[启动] 股票列表更新失败（耗时 %.1fs）: %s", elapsed, e)


async def sync_from_progress(skip_check: bool = False) -> None:
    """启动时基于进度表恢复同步（替代旧的 check_data_integrity）。

    流程：交易日检查 → 获取同步锁 → reset_stale_status → 初始化进度表 →
    同步退市状态 → 查询待处理股票 → 批量处理 → 完成率日志 → 释放锁

    Args:
        skip_check: 是否跳过检查
    """
    if not settings.data_integrity_check_enabled or skip_check:
        if skip_check:
            logger.info("[启动同步] 已跳过（--skip-integrity-check）")
        else:
            logger.info("[启动同步] 已禁用（DATA_INTEGRITY_CHECK_ENABLED=false）")
        return

    start = time.monotonic()
    logger.info("[启动同步] 开始基于进度表恢复同步")

    try:
        from app.data.manager import DataManager
        from app.data.tushare import TushareClient
        from app.database import async_session_factory
        from app.models.market import TradeCalendar
        from sqlalchemy import select

        client = TushareClient()
        manager = DataManager(
            session_factory=async_session_factory,
            clients={"tushare": client},
            primary="tushare",
        )

        # 查询最近的交易日作为目标日期（避免非交易日无效同步）
        today = date.today()
        async with async_session_factory() as session:
            stmt = (
                select(TradeCalendar.cal_date)
                .where(
                    TradeCalendar.is_open == True,
                    TradeCalendar.cal_date <= today,
                )
                .order_by(TradeCalendar.cal_date.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            latest_trade_date = result.scalar_one_or_none()

        if latest_trade_date is None:
            elapsed = time.monotonic() - start
            logger.warning("[启动同步] 交易日历为空，跳过（耗时 %.1fs）", elapsed)
            return

        target_date = latest_trade_date
        if target_date != today:
            logger.info("[启动同步] 今天非交易日，使用最近交易日：%s", target_date)

        # 获取同步锁
        if not await manager.acquire_sync_lock():
            logger.warning("[启动同步] 同步锁被占用，跳过")
            return

        try:
            # 重置 stale 状态
            stale_count = await manager.reset_stale_status()

            # 初始化进度表
            init_result = await manager.init_sync_progress()

            # 同步退市状态
            delisted_result = await manager.sync_delisted_status()

            # 查询待处理股票
            needing_sync = await manager.get_stocks_needing_sync(target_date)

            if not needing_sync:
                summary = await manager.get_sync_summary(target_date)
                elapsed = time.monotonic() - start
                logger.info(
                    "[启动同步] 无需同步，完成率 %.1f%%，耗时 %.1fs",
                    summary["completion_rate"] * 100, elapsed,
                )
                return

            logger.info("[启动同步] 待同步股票 %d 只", len(needing_sync))

            # 批量处理
            await manager.process_stocks_batch(
                needing_sync,
                target_date,
                concurrency=settings.daily_sync_concurrency,
                timeout=settings.sync_batch_timeout,
            )

            # 完成率日志
            summary = await manager.get_sync_summary(target_date)
            elapsed = time.monotonic() - start
            logger.info(
                "[启动同步] 完成：完成率 %.1f%%（%d/%d），失败 %d，耗时 %.1fs",
                summary["completion_rate"] * 100,
                summary["data_done"], summary["total"],
                summary["failed"], elapsed,
            )
        finally:
            await manager.release_sync_lock()

    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error("[启动同步] 失败（耗时 %.1fs）: %s", elapsed, e, exc_info=True)


async def start_scheduler(skip_integrity_check: bool = False) -> None:
    """启动调度器，注册所有任务。供 FastAPI lifespan 调用。

    Args:
        skip_integrity_check: 是否跳过数据完整性检查
    """
    global _scheduler

    # 启动时清除旧的同步锁（避免上次异常退出残留的锁阻塞同步）
    from app.cache.redis_client import get_redis

    try:
        redis = await get_redis()
        if redis:
            await redis.delete("stock_selector:sync_lock")
            logger.info("[启动] 已清除旧的同步锁")
    except Exception as e:
        logger.warning("[启动] 清除同步锁失败（可忽略）: %s", e)

    # 启动时更新股票列表
    await sync_stock_list_on_startup()

    # 基于进度表恢复同步
    await sync_from_progress(skip_check=skip_integrity_check)

    # 创建并启动调度器
    _scheduler = create_scheduler()
    register_jobs(_scheduler)
    _scheduler.start()
    logger.info("调度器已启动")


async def stop_scheduler() -> None:
    """优雅停止调度器，等待运行中的任务完成。"""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=True)
        logger.info("调度器已停止")
        _scheduler = None
