"""调度器核心：创建、配置、启动和停止 APScheduler。"""

import logging

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
    from app.scheduler.jobs import run_post_market_chain, sync_stock_list_job

    # 盘后链路：默认周一至周五 15:30
    post_market_cron = settings.scheduler_post_market_cron
    parts = post_market_cron.split()
    scheduler.add_job(
        func=run_post_market_chain,
        trigger=CronTrigger(
            minute=parts[0],
            hour=parts[1],
            day=parts[2],
            month=parts[3],
            day_of_week=parts[4],
            timezone="Asia/Shanghai",
        ),
        id="post_market_chain",
        name="盘后链路",
        replace_existing=True,
    )
    logger.info("注册任务：盘后链路 [%s]", post_market_cron)

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


async def start_scheduler() -> None:
    """启动调度器，注册所有任务。供 FastAPI lifespan 调用。"""
    global _scheduler
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
