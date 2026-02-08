"""定时任务定义：盘后链路、周末维护等。"""

import logging
import time
import traceback
from datetime import date

from app.cache.redis_client import get_redis
from app.cache.tech_cache import refresh_all_tech_cache
from app.data.akshare import AKShareClient
from app.data.baostock import BaoStockClient
from app.data.indicator import compute_incremental
from app.data.manager import DataManager
from app.database import async_session_factory
from app.strategy.factory import StrategyFactory
from app.strategy.pipeline import execute_pipeline

logger = logging.getLogger(__name__)


def _build_manager() -> DataManager:
    """构造 DataManager 实例。"""
    clients = {
        "baostock": BaoStockClient(),
        "akshare": AKShareClient(),
    }
    return DataManager(
        session_factory=async_session_factory,
        clients=clients,
        primary="baostock",
    )


async def run_post_market_chain(target_date: date | None = None) -> None:
    """盘后链路：交易日校验 → 日线同步 → 技术指标 → 缓存刷新 → 策略管道。

    任一关键步骤失败则中断链路，缓存刷新失败不阻断。

    Args:
        target_date: 目标日期，默认今天
    """
    target = target_date or date.today()
    chain_start = time.monotonic()
    logger.info("===== 盘后链路开始：%s =====", target)

    # 交易日校验
    manager = _build_manager()
    is_trading = await manager.is_trade_day(target)
    if not is_trading:
        logger.info("非交易日，跳过盘后任务：%s", target)
        return

    # 步骤 1：日线同步
    try:
        await sync_daily_step(target, manager)
    except Exception:
        logger.error("盘后链路中断：日线同步失败\n%s", traceback.format_exc())
        return

    # 步骤 2：技术指标计算
    try:
        await indicator_step(target)
    except Exception:
        logger.error("盘后链路中断：技术指标计算失败\n%s", traceback.format_exc())
        return

    # 步骤 3：缓存刷新（非关键，失败不阻断）
    await cache_refresh_step(target)

    # 步骤 4：策略管道执行
    try:
        await pipeline_step(target)
    except Exception:
        logger.error("盘后链路中断：策略管道执行失败\n%s", traceback.format_exc())
        return

    elapsed = int(time.monotonic() - chain_start)
    logger.info("===== 盘后链路完成：%s，总耗时 %ds =====", target, elapsed)


async def sync_daily_step(
    target_date: date,
    manager: DataManager | None = None,
) -> None:
    """日线增量同步：查询所有上市股票，逐只同步当日数据。

    Args:
        target_date: 目标日期
        manager: DataManager 实例（可选，默认自动构建）
    """
    mgr = manager or _build_manager()
    step_start = time.monotonic()
    logger.info("[日线同步] 开始：%s", target_date)

    stocks = await mgr.get_stock_list(status="L")
    success_count = 0
    fail_count = 0

    for stock in stocks:
        code = stock["ts_code"]
        try:
            await mgr.sync_daily(code, target_date, target_date)
            success_count += 1
        except Exception as e:
            fail_count += 1
            logger.warning("[日线同步] %s 失败：%s", code, e)

    elapsed = int(time.monotonic() - step_start)
    logger.info(
        "[日线同步] 完成：成功 %d 只，失败 %d 只，耗时 %ds",
        success_count, fail_count, elapsed,
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
        elapsed = int(time.monotonic() - step_start)
        logger.info("[缓存刷新] 完成：%d 只股票，耗时 %ds", count, elapsed)
    except Exception as e:
        logger.warning("缓存刷新失败，策略管道将回源数据库：%s", e)


async def indicator_step(target_date: date) -> None:
    """增量计算技术指标。

    Args:
        target_date: 目标日期
    """
    step_start = time.monotonic()
    logger.info("[技术指标] 开始：%s", target_date)

    result = await compute_incremental(
        async_session_factory, target_date=target_date
    )

    elapsed = int(time.monotonic() - step_start)
    logger.info("[技术指标] 完成：%s，耗时 %ds", result, elapsed)


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
    logger.info("[股票列表同步] 开始")
    manager = _build_manager()
    result = await manager.sync_stock_list()
    logger.info("[股票列表同步] 完成：%s", result)
