"""自动数据更新任务模块：智能触发数据同步和重试。

实现每日自动触发、数据嗅探、智能重试和超时报警功能。
"""

import logging
import traceback
from datetime import date, datetime, time

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.cache.redis_client import get_redis
from app.config import settings
from app.data.manager import DataManager
from app.data.tushare import TushareClient
from app.data.probe import probe_daily_data
from app.database import async_session_factory
from app.notification import NotificationLevel, NotificationManager
from app.scheduler.jobs import run_post_market_chain
from app.scheduler.state import SyncState, SyncStateManager

logger = logging.getLogger(__name__)


def _build_manager() -> DataManager:
    """构造 DataManager 实例（使用 TushareClient）。"""
    client = TushareClient()
    return DataManager(
        session_factory=async_session_factory,
        clients={"tushare": client},
        primary="tushare",
    )


async def auto_update_job(target_date: date | None = None) -> None:
    """自动数据更新任务（每日 15:30 触发）。

    工作流程：
    1. 检查是否交易日
    2. 检查任务状态（避免重复执行）
    3. 数据嗅探
    4. 如有数据 → 执行盘后链路
    5. 如无数据 → 启动定时嗅探任务

    Args:
        target_date: 目标日期，默认今天
    """
    target = target_date or date.today()
    logger.info("===== [自动数据更新] 开始：%s =====", target)

    # 初始化状态管理器和通知管理器
    redis = get_redis()
    state_manager = SyncStateManager(redis)
    notifier = NotificationManager()

    # 步骤 1：交易日校验
    manager = _build_manager()
    is_trading = await manager.is_trade_day(target)
    if not is_trading:
        logger.info("[自动数据更新] 非交易日，跳过：%s", target)
        return

    # 步骤 2：任务状态检查（避免重复执行）
    if await state_manager.is_completed(target):
        logger.info("[自动数据更新] 任务已完成，跳过：%s", target)
        return

    current_state = await state_manager.get_state(target)
    if current_state in (SyncState.SYNCING, SyncState.PROBING):
        logger.info("[自动数据更新] 任务进行中（%s），跳过：%s", current_state.value, target)
        return

    # 步骤 3：数据嗅探
    logger.info("[自动数据更新] 开始数据嗅探：%s", target)
    is_ready = await probe_daily_data(
        session_factory=async_session_factory,
        target_date=target,
        probe_stocks=settings.auto_update_probe_stocks,
        threshold=settings.auto_update_probe_threshold,
    )

    if is_ready:
        # 步骤 4：数据已就绪，立即执行盘后链路
        logger.info("[自动数据更新] 数据已就绪，开始执行盘后链路：%s", target)
        await state_manager.set_state(target, SyncState.SYNCING)

        try:
            await run_post_market_chain(target)
            await state_manager.set_state(target, SyncState.COMPLETED)
            logger.info("===== [自动数据更新] 完成：%s =====", target)
        except Exception:
            await state_manager.set_state(target, SyncState.FAILED)
            error_msg = traceback.format_exc()
            logger.error("[自动数据更新] 盘后链路执行失败：%s\n%s", target, error_msg)
            await notifier.send(
                level=NotificationLevel.ERROR,
                title="数据同步失败",
                message=f"{target} 盘后链路执行失败",
                metadata={"date": str(target), "error": error_msg[:500]},
            )
    else:
        # 步骤 5：数据未就绪，启动定时嗅探任务
        logger.info("[自动数据更新] 数据未就绪，启动定时嗅探任务：%s", target)
        await state_manager.set_state(target, SyncState.PROBING)

        # 获取调度器实例
        from app.scheduler.core import _scheduler

        if _scheduler is None:
            logger.error("[自动数据更新] 调度器未初始化，无法启动嗅探任务")
            return

        # 添加嗅探任务（每 N 分钟触发一次）
        job_id = f"probe_and_sync_{target.isoformat()}"
        _scheduler.add_job(
            func=probe_and_sync_job,
            trigger=IntervalTrigger(minutes=settings.auto_update_probe_interval),
            args=[target],
            id=job_id,
            name=f"数据嗅探任务 [{target}]",
            replace_existing=True,
        )
        await state_manager.save_probe_job_id(target, job_id)
        logger.info(
            "[自动数据更新] 嗅探任务已启动：%s，间隔 %d 分钟",
            job_id,
            settings.auto_update_probe_interval,
        )


async def probe_and_sync_job(target_date: date) -> None:
    """定时嗅探任务（每 N 分钟触发一次）。

    工作流程：
    1. 检查任务状态（如已完成则跳过）
    2. 检查是否超时（18:00）
    3. 数据嗅探
    4. 如有数据 → 执行盘后链路 → 停止嗅探任务
    5. 如无数据 → 继续等待下次嗅探
    6. 如超时 → 发送报警 → 停止嗅探任务

    Args:
        target_date: 目标日期
    """
    logger.info("[嗅探任务] 触发：%s", target_date)

    # 初始化状态管理器和通知管理器
    redis = get_redis()
    state_manager = SyncStateManager(redis)
    notifier = NotificationManager()

    # 步骤 1：任务状态检查
    if await state_manager.is_completed(target_date):
        logger.info("[嗅探任务] 任务已完成，停止嗅探：%s", target_date)
        await _stop_probe_job(state_manager, target_date)
        return

    # 递增嗅探计数
    probe_count = await state_manager.increment_probe_count(target_date)
    logger.info("[嗅探任务] 第 %d 次嗅探：%s", probe_count, target_date)

    # 步骤 2：超时检查
    timeout_time = datetime.strptime(settings.auto_update_probe_timeout, "%H:%M").time()
    current_time = datetime.now().time()

    if current_time >= timeout_time:
        logger.error("[嗅探任务] 超时（%s），停止嗅探：%s", timeout_time, target_date)
        await state_manager.set_state(target_date, SyncState.FAILED)
        await notifier.send(
            level=NotificationLevel.ERROR,
            title="数据同步超时",
            message=f"{target_date} 数据嗅探超时，{timeout_time} 仍无数据",
            metadata={"date": str(target_date), "probe_count": probe_count},
        )
        await _stop_probe_job(state_manager, target_date)
        return

    # 步骤 3：数据嗅探
    is_ready = await probe_daily_data(
        session_factory=async_session_factory,
        target_date=target_date,
        probe_stocks=settings.auto_update_probe_stocks,
        threshold=settings.auto_update_probe_threshold,
    )

    if is_ready:
        # 步骤 4：数据已就绪，执行盘后链路
        logger.info("[嗅探任务] 数据已就绪，开始执行盘后链路：%s", target_date)
        await state_manager.set_state(target_date, SyncState.SYNCING)

        try:
            await run_post_market_chain(target_date)
            await state_manager.set_state(target_date, SyncState.COMPLETED)
            logger.info("[嗅探任务] 盘后链路执行成功，停止嗅探：%s", target_date)
        except Exception:
            await state_manager.set_state(target_date, SyncState.FAILED)
            error_msg = traceback.format_exc()
            logger.error("[嗅探任务] 盘后链路执行失败：%s\n%s", target_date, error_msg)
            await notifier.send(
                level=NotificationLevel.ERROR,
                title="数据同步失败",
                message=f"{target_date} 盘后链路执行失败",
                metadata={"date": str(target_date), "probe_count": probe_count, "error": error_msg[:500]},
            )

        await _stop_probe_job(state_manager, target_date)
    else:
        # 步骤 5：数据未就绪，继续等待下次嗅探
        logger.info("[嗅探任务] 数据未就绪，继续等待：%s", target_date)


async def _stop_probe_job(state_manager: SyncStateManager, target_date: date) -> None:
    """停止嗅探任务。

    Args:
        state_manager: 状态管理器
        target_date: 目标日期
    """
    job_id = await state_manager.get_probe_job_id(target_date)
    if job_id is None:
        logger.debug("[嗅探任务] 无任务 ID 记录，跳过停止：%s", target_date)
        return

    from app.scheduler.core import _scheduler

    if _scheduler is None:
        logger.warning("[嗅探任务] 调度器未初始化，无法停止任务：%s", job_id)
        return

    try:
        _scheduler.remove_job(job_id)
        logger.info("[嗅探任务] 已停止：%s", job_id)
    except Exception as e:
        logger.warning("[嗅探任务] 停止失败：%s，错误：%s", job_id, e)
