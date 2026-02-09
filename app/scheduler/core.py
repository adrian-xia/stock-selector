"""调度器核心：创建、配置、启动和停止 APScheduler。"""

import logging
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
    from app.scheduler.jobs import sync_stock_list_job

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


async def check_data_integrity(skip_check: bool = False) -> None:
    """启动时数据完整性检查，自动补齐缺失的交易日数据。

    检查最近 N 天（由 DATA_INTEGRITY_CHECK_DAYS 配置）的数据完整性，
    如果发现缺失的交易日，自动调用批量同步补齐。

    Args:
        skip_check: 是否跳过检查（通过 --skip-integrity-check 参数传入）
    """
    # 检查是否启用
    if not settings.data_integrity_check_enabled or skip_check:
        if skip_check:
            logger.info("[数据完整性检查] 已跳过（--skip-integrity-check）")
        else:
            logger.info("[数据完整性检查] 已禁用（DATA_INTEGRITY_CHECK_ENABLED=false）")
        return

    logger.info("[数据完整性检查] 开始检查最近 %d 天数据", settings.data_integrity_check_days)

    try:
        # 导入依赖（延迟导入避免循环依赖）
        from app.data.akshare import AKShareClient
        from app.data.baostock import BaoStockClient
        from app.data.batch import batch_sync_daily
        from app.data.manager import DataManager
        from app.data.pool import get_pool
        from app.database import async_session_factory

        # 构建 DataManager
        pool = get_pool()
        clients = {
            "baostock": BaoStockClient(connection_pool=pool),
            "akshare": AKShareClient(),
        }
        manager = DataManager(
            session_factory=async_session_factory,
            clients=clients,
            primary="baostock",
        )

        # 计算检查日期范围：最近 N 天
        end_date = date.today()
        start_date = end_date - timedelta(days=settings.data_integrity_check_days)

        # 检测缺失日期
        missing_dates = await manager.detect_missing_dates(start_date, end_date)

        if not missing_dates:
            logger.info("[数据完整性检查] 最近 %d 天数据完整", settings.data_integrity_check_days)
            return

        logger.warning(
            "[数据完整性检查] 发现 %d 个缺失交易日，开始自动补齐：%s",
            len(missing_dates),
            [d.isoformat() for d in missing_dates[:5]] + (["..."] if len(missing_dates) > 5 else []),
        )

        # 获取所有上市股票
        stocks = await manager.get_stock_list(status="L")
        stock_codes = [s["ts_code"] for s in stocks]

        # 逐个缺失日期补齐
        for missing_date in missing_dates:
            logger.info("[数据完整性检查] 补齐日期：%s", missing_date)
            try:
                result = await batch_sync_daily(
                    session_factory=async_session_factory,
                    stock_codes=stock_codes,
                    target_date=missing_date,
                    connection_pool=pool,
                )
                logger.info(
                    "[数据完整性检查] 日期 %s 补齐完成：成功 %d 只，失败 %d 只",
                    missing_date, result["success"], result["failed"],
                )
            except Exception as e:
                logger.error(
                    "[数据完整性检查] 日期 %s 补齐失败：%s",
                    missing_date, e,
                )
                # 继续补齐其他日期，不中断

        logger.info("[数据完整性检查] 完成，共补齐 %d 个交易日", len(missing_dates))

    except Exception as e:
        logger.error("[数据完整性检查] 检查失败：%s", e, exc_info=True)
        # 检查失败不阻断调度器启动


async def start_scheduler(skip_integrity_check: bool = False) -> None:
    """启动调度器，注册所有任务。供 FastAPI lifespan 调用。

    Args:
        skip_integrity_check: 是否跳过数据完整性检查
    """
    global _scheduler

    # 启动前数据完整性检查
    await check_data_integrity(skip_check=skip_integrity_check)

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
