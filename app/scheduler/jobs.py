"""定时任务定义：盘后链路、周末维护、失败重试等。"""

import logging
import time
import traceback
from datetime import date, datetime

from app.cache.redis_client import get_redis
from app.cache.tech_cache import refresh_all_tech_cache
from app.config import settings
from app.data.manager import DataManager
from app.data.tushare import TushareClient
from app.database import async_session_factory
from app.strategy.factory import StrategyFactory
from app.strategy.pipeline import execute_pipeline

logger = logging.getLogger(__name__)


def _build_manager() -> DataManager:
    """构造 DataManager 实例（使用 TushareClient）。"""
    client = TushareClient()
    return DataManager(
        session_factory=async_session_factory,
        clients={"tushare": client},
        primary="tushare",
    )


async def run_post_market_chain(target_date: date | None = None) -> None:
    """盘后链路：同步锁 → 股票列表 → 进度初始化 → 批量处理 → 完整性门控 → 策略 → 释放锁。

    使用进度表驱动，支持断点续传。任一关键步骤失败则中断链路。

    Args:
        target_date: 目标日期，默认今天
    """
    target = target_date or date.today()
    chain_start = time.monotonic()
    logger.info("===== [盘后链路] 开始：%s =====", target)

    manager = _build_manager()

    # 步骤 0：交易日历更新（非关键，失败不阻断）
    calendar_start = time.monotonic()
    try:
        calendar_result = await manager.sync_trade_calendar()
        logger.info("[交易日历更新] 完成：%s，耗时 %.2fs", calendar_result, time.monotonic() - calendar_start)
    except Exception:
        logger.warning("[交易日历更新] 失败（继续执行），耗时 %.2fs\n%s", time.monotonic() - calendar_start, traceback.format_exc())

    # 交易日校验
    is_trading = await manager.is_trade_day(target)
    if not is_trading:
        logger.info("[盘后链路] 非交易日，跳过：%s", target)
        return

    # 获取同步锁
    if not await manager.acquire_sync_lock():
        logger.warning("[盘后链路] 同步锁被占用，跳过：%s", target)
        return

    try:
        # 步骤 1：更新股票列表
        stock_list_start = time.monotonic()
        try:
            stock_result = await manager.sync_stock_list()
            logger.info("[股票列表更新] 完成：%s，耗时 %.1fs", stock_result, time.monotonic() - stock_list_start)
        except Exception:
            logger.warning("[股票列表更新] 失败（继续执行），耗时 %.1fs\n%s", time.monotonic() - stock_list_start, traceback.format_exc())

        # 步骤 2：重置 stale 状态 + 初始化进度表 + 同步退市状态
        stale_count = await manager.reset_stale_status()
        if stale_count > 0:
            logger.info("[盘后链路] 重置 stale 状态：%d 条", stale_count)

        init_result = await manager.init_sync_progress()
        logger.info("[盘后链路] 进度表初始化：%s", init_result)

        delisted_result = await manager.sync_delisted_status()
        logger.info("[盘后链路] 退市状态同步：%s", delisted_result)

        # 步骤 3：批量数据拉取 + 指标计算
        needing_sync = await manager.get_stocks_needing_sync(target)
        if needing_sync:
            logger.info("[盘后链路] 待同步股票 %d 只", len(needing_sync))
            await manager.process_stocks_batch(
                needing_sync,
                target,
                concurrency=settings.daily_sync_concurrency,
                timeout=settings.sync_batch_timeout,
            )

        # 步骤 3.5：资金流向同步（非关键，失败不阻断）
        moneyflow_start = time.monotonic()
        try:
            mf_result = await manager.sync_raw_moneyflow(target)
            tl_result = await manager.sync_raw_top_list(target)
            etl_result = await manager.etl_moneyflow(target)
            logger.info(
                "[资金流向同步] 完成：raw=%s, top=%s, etl=%s，耗时 %.1fs",
                mf_result, tl_result, etl_result, time.monotonic() - moneyflow_start,
            )
        except Exception:
            logger.warning(
                "[资金流向同步] 失败（继续执行），耗时 %.1fs\n%s",
                time.monotonic() - moneyflow_start, traceback.format_exc(),
            )

        # 步骤 4：缓存刷新（非关键，失败不阻断）
        await cache_refresh_step(target)

        # 步骤 5：完整性门控 → 策略执行/跳过
        summary = await manager.get_sync_summary(target)
        completion_rate = summary["completion_rate"]
        threshold = settings.data_completeness_threshold

        if completion_rate >= threshold:
            logger.info(
                "[完整性门控] 通过：完成率 %.1f%% >= 阈值 %.1f%%，执行策略",
                completion_rate * 100, threshold * 100,
            )
            try:
                await pipeline_step(target)
            except Exception:
                logger.error("[盘后链路] 策略管道执行失败\n%s", traceback.format_exc())
        else:
            logger.warning(
                "[完整性门控] 未通过：完成率 %.1f%% < 阈值 %.1f%%，跳过策略（总 %d，完成 %d，失败 %d）",
                completion_rate * 100, threshold * 100,
                summary["total"], summary["data_done"], summary["failed"],
            )

        # 步骤 6：完整性告警（超过截止时间且有失败记录）
        _check_completeness_deadline(summary, target)

    finally:
        await manager.release_sync_lock()

    elapsed = time.monotonic() - chain_start
    elapsed_minutes = int(elapsed / 60)
    elapsed_seconds = int(elapsed % 60)
    logger.info(
        "===== [盘后链路] 完成：%s，总耗时 %d分%d秒 (%.1fs) =====",
        target, elapsed_minutes, elapsed_seconds, elapsed,
    )


def _check_completeness_deadline(summary: dict, target_date: date) -> None:
    """检查完整性告警：超过截止时间且有失败记录时发出告警。

    Args:
        summary: get_sync_summary() 返回的摘要
        target_date: 目标日期
    """
    if summary["failed"] == 0:
        return

    deadline_str = settings.pipeline_completeness_deadline
    deadline_time = datetime.strptime(deadline_str, "%H:%M").time()
    current_time = datetime.now().time()

    if current_time >= deadline_time:
        logger.warning(
            "[完整性告警] %s 超过截止时间 %s，仍有 %d 只股票失败（完成率 %.1f%%）",
            target_date, deadline_str, summary["failed"],
            summary["completion_rate"] * 100,
        )


async def cache_refresh_step(target_date: date) -> None:
    """刷新技术指标缓存（非关键步骤，失败不阻断链路）。

    Args:
        target_date: 目标日期
    """
    redis = get_redis()
    if redis is None:
        logger.warning("[缓存刷新] Redis 不可用，跳过")
        return

    step_start = time.monotonic()
    logger.info("[缓存刷新] 开始：%s", target_date)

    try:
        count = await refresh_all_tech_cache(redis, async_session_factory)
        elapsed = time.monotonic() - step_start
        logger.info("[缓存刷新] 完成：%d 只股票，总耗时 %.1fs", count, elapsed)
    except Exception as e:
        elapsed = time.monotonic() - step_start
        logger.warning("[缓存刷新] 失败（耗时 %.1fs），策略管道将回源数据库：%s", elapsed, e)


async def pipeline_step(target_date: date) -> None:
    """执行策略管道：使用全部已注册策略。

    Args:
        target_date: 目标日期
    """
    step_start = time.monotonic()
    logger.info("[策略管道] 开始：%s", target_date)

    # 获取全部策略名称
    all_strategies = StrategyFactory.get_all()
    strategy_names = [m.name for m in all_strategies]

    result = await execute_pipeline(
        session_factory=async_session_factory,
        strategy_names=strategy_names,
        target_date=target_date,
        top_n=50,
    )

    elapsed = int(time.monotonic() - step_start)
    logger.info(
        "[策略管道] 完成：筛选出 %d 只，耗时 %dms",
        len(result.picks), result.elapsed_ms,
    )


async def sync_stock_list_job() -> None:
    """周末股票列表全量同步。"""
    manager = _build_manager()

    # 步骤 1：更新交易日历
    logger.info("[交易日历更新] 开始")
    try:
        calendar_result = await manager.sync_trade_calendar()
        logger.info("[交易日历更新] 完成：%s", calendar_result)
    except Exception:
        logger.error("[交易日历更新] 失败，继续执行股票列表同步\n%s", traceback.format_exc())

    # 步骤 2：同步股票列表
    logger.info("[股票列表同步] 开始")
    result = await manager.sync_stock_list()
    logger.info("[股票列表同步] 完成：%s", result)


async def retry_failed_stocks_job() -> None:
    """定时重试失败股票：获取同步锁 → 查询失败股票 → 逐只重试 → 检查完整性 → 释放锁。

    每次重试 retry_count+1，超过 max_retries 的股票记录 WARNING 不再重试。
    重试完成后检查完整性，达到阈值则补跑策略。
    """
    target = date.today()
    start = time.monotonic()
    logger.info("[失败重试] 开始：%s", target)

    manager = _build_manager()
    max_retries = settings.batch_sync_max_retries

    # 获取同步锁
    if not await manager.acquire_sync_lock():
        logger.warning("[失败重试] 同步锁被占用，跳过")
        return

    try:
        # 查询可重试的失败股票
        failed_stocks = await manager.get_failed_stocks(max_retries)
        if not failed_stocks:
            logger.info("[失败重试] 无需重试的失败股票")
            return

        logger.info("[失败重试] 待重试股票 %d 只", len(failed_stocks))

        # 检查超过重试上限的股票
        all_failed = await manager.get_failed_stocks(max_retries=999999)
        exceeded = [s for s in all_failed if s["retry_count"] >= max_retries]
        if exceeded:
            codes = [s["ts_code"] for s in exceeded[:10]]
            logger.warning(
                "[失败重试] %d 只股票超过最大重试次数 %d，不再自动重试：%s%s",
                len(exceeded), max_retries, codes,
                "..." if len(exceeded) > 10 else "",
            )

        # 递增 retry_count 并重置状态为 idle，然后重新处理
        from sqlalchemy import update as sa_update
        from app.models.market import StockSyncProgress

        success_count = 0
        fail_count = 0
        for stock in failed_stocks:
            ts_code = stock["ts_code"]
            try:
                # 递增 retry_count
                async with manager.session_factory() as session:
                    await session.execute(
                        sa_update(StockSyncProgress)
                        .where(StockSyncProgress.ts_code == ts_code)
                        .values(retry_count=StockSyncProgress.retry_count + 1, status="idle")
                    )
                    await session.commit()

                # 从 data_date 恢复同步
                await manager.process_single_stock(ts_code, target)
                success_count += 1
            except Exception as e:
                fail_count += 1
                logger.error("[失败重试] %s 重试失败：%s", ts_code, e)

        elapsed = time.monotonic() - start
        logger.info(
            "[失败重试] 完成：成功 %d，失败 %d，耗时 %.1fs",
            success_count, fail_count, elapsed,
        )

        # 重试后检查完整性，达到阈值则补跑策略
        summary = await manager.get_sync_summary(target)
        completion_rate = summary["completion_rate"]
        threshold = settings.data_completeness_threshold

        if completion_rate >= threshold:
            logger.info(
                "[失败重试] 完成率 %.1f%% >= 阈值 %.1f%%，补跑策略",
                completion_rate * 100, threshold * 100,
            )
            try:
                await pipeline_step(target)
            except Exception:
                logger.error("[失败重试] 补跑策略失败\n%s", traceback.format_exc())
        else:
            logger.info(
                "[失败重试] 完成率 %.1f%% < 阈值 %.1f%%，跳过策略",
                completion_rate * 100, threshold * 100,
            )

    finally:
        await manager.release_sync_lock()
