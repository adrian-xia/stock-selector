import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.ai import router as ai_router
from app.api.alert import router as alert_router
from app.api.backtest import router as backtest_router
from app.api.data import router as data_router
from app.api.health import router as health_router
from app.api.middleware import RequestPerformanceMiddleware
from app.api.news import router as news_router
from app.api.optimization import router as optimization_router
from app.api.realtime import router as realtime_router
from app.api.strategy import router as strategy_router
from app.api.task_log import router as task_log_router
from app.api.websocket import router as ws_router
from app.api.research import router as research_router
from app.v4backtest.router import router as v4backtest_router
from app.cache.redis_client import close_redis, get_redis, init_redis
from app.cache.tech_cache import warmup_cache
from app.config import settings
from app.database import async_session_factory, engine
from app.logger import setup_logging
from app.scheduler.core import start_scheduler, stop_scheduler
from app.strategy.base import StrategyRole
from app.strategy.factory import STRATEGY_REGISTRY, StrategyFactoryV2, resolve_v2_default_params

logger = logging.getLogger(__name__)

# 优雅关闭超时时间（秒）
_shutdown_timeout = 30


async def _graceful_shutdown() -> None:
    """优雅关闭逻辑：等待运行中的任务完成，超时后强制关闭。"""
    logger.info("[关闭] 停止接受新任务，等待运行中的任务完成...")
    logger.info("[关闭] 超时时间：%d 秒", _shutdown_timeout)

    try:
        # 停止调度器（等待运行中的任务完成）
        await asyncio.wait_for(
            stop_scheduler(),
            timeout=_shutdown_timeout,
        )
        logger.info("[关闭] 调度器已停止，所有任务已完成")

    except asyncio.TimeoutError:
        logger.warning(
            "[关闭] 等待超时（%d 秒），强制关闭调度器",
            _shutdown_timeout,
        )
        # 超时后强制停止（stop_scheduler 内部已经处理了强制停止）
        await stop_scheduler()

    # 关闭其他资源
    logger.info("[关闭] 关闭数据库连接...")
    await close_redis()
    await engine.dispose()

    logger.info("[关闭] 完成")


def _build_active_strategy_rows() -> list[dict]:
    """构造当前活跃策略元数据。"""
    trigger_metas = StrategyFactoryV2.get_by_role(StrategyRole.TRIGGER)
    rows = [
        {
            "name": meta.name,
            "category": meta.signal_group.value if meta.signal_group else meta.role.value,
            "description": meta.description or "",
            "params": json.dumps(resolve_v2_default_params(meta)),
            "role": meta.role.value,
            "signal_group": meta.signal_group.value if meta.signal_group else None,
            "ai_rating": float(meta.ai_rating),
        }
        for meta in trigger_metas
    ]
    rows.extend(
        {
            "name": meta.name,
            "category": meta.category,
            "description": meta.description or "",
            "params": json.dumps(meta.default_params),
            "role": "legacy",
            "signal_group": None,
            "ai_rating": None,
        }
        for meta in STRATEGY_REGISTRY.values()
    )
    return rows


async def _cleanup_obsolete_strategy_data(
    session: AsyncSession,
    active_names: list[str],
) -> dict[str, int]:
    """物理清理已废弃策略及其历史数据。"""
    select_sql = (
        text("SELECT id, name FROM strategies WHERE name NOT IN :active_names")
        .bindparams(bindparam("active_names", expanding=True))
    )
    result = await session.execute(select_sql, {"active_names": active_names})
    obsolete_rows = result.fetchall()

    if not obsolete_rows:
        return {"strategies": 0}

    obsolete_ids = [int(row[0]) for row in obsolete_rows]
    obsolete_names = [str(row[1]) for row in obsolete_rows]

    stats = {"strategies": len(obsolete_names)}

    delete_specs = [
        (
            "optimization_results",
            text("""
                DELETE FROM optimization_results
                WHERE task_id IN (
                    SELECT id FROM optimization_tasks
                    WHERE strategy_name IN :obsolete_names
                )
            """).bindparams(bindparam("obsolete_names", expanding=True)),
            {"obsolete_names": obsolete_names},
        ),
        (
            "optimization_tasks",
            text("DELETE FROM optimization_tasks WHERE strategy_name IN :obsolete_names")
            .bindparams(bindparam("obsolete_names", expanding=True)),
            {"obsolete_names": obsolete_names},
        ),
        (
            "market_optimization_tasks",
            text("DELETE FROM market_optimization_tasks WHERE strategy_name IN :obsolete_names")
            .bindparams(bindparam("obsolete_names", expanding=True)),
            {"obsolete_names": obsolete_names},
        ),
        (
            "strategy_picks",
            text("DELETE FROM strategy_picks WHERE strategy_name IN :obsolete_names")
            .bindparams(bindparam("obsolete_names", expanding=True)),
            {"obsolete_names": obsolete_names},
        ),
        (
            "strategy_hit_stats",
            text("DELETE FROM strategy_hit_stats WHERE strategy_name IN :obsolete_names")
            .bindparams(bindparam("obsolete_names", expanding=True)),
            {"obsolete_names": obsolete_names},
        ),
        (
            "trade_plans",
            text("DELETE FROM trade_plans WHERE source_strategy IN :obsolete_names")
            .bindparams(bindparam("obsolete_names", expanding=True)),
            {"obsolete_names": obsolete_names},
        ),
        (
            "strategy_watchpool",
            text("DELETE FROM strategy_watchpool WHERE strategy_name IN :obsolete_names")
            .bindparams(bindparam("obsolete_names", expanding=True)),
            {"obsolete_names": obsolete_names},
        ),
        (
            "backtest_results",
            text("""
                DELETE FROM backtest_results
                WHERE task_id IN (
                    SELECT id FROM backtest_tasks
                    WHERE strategy_id IN :obsolete_ids
                )
            """).bindparams(bindparam("obsolete_ids", expanding=True)),
            {"obsolete_ids": obsolete_ids},
        ),
        (
            "backtest_tasks",
            text("DELETE FROM backtest_tasks WHERE strategy_id IN :obsolete_ids")
            .bindparams(bindparam("obsolete_ids", expanding=True)),
            {"obsolete_ids": obsolete_ids},
        ),
        (
            "strategies",
            text("DELETE FROM strategies WHERE id IN :obsolete_ids")
            .bindparams(bindparam("obsolete_ids", expanding=True)),
            {"obsolete_ids": obsolete_ids},
        ),
    ]

    for key, sql, params in delete_specs:
        delete_result = await session.execute(sql, params)
        stats[key] = delete_result.rowcount or 0

    logger.info(
        "[策略清理] 删除废弃策略 %d 个：%s",
        len(obsolete_names),
        obsolete_names,
    )
    return stats


async def _sync_strategies_to_db() -> None:
    """将内存中注册的策略同步到 strategies 表，并清理废弃策略。

    - 仅同步当前仍在使用的策略：
      - V2 trigger（策略配置/执行入口）
      - V4 `volume-price-pattern`（独立链路仍在使用）
    - 同时物理删除数据库中的废弃 V1 策略及其关联历史
    """
    active_rows = _build_active_strategy_rows()
    active_names = sorted(row["name"] for row in active_rows)

    async with async_session_factory() as session:
        for row in active_rows:
            await session.execute(
                text("""
                    INSERT INTO strategies (
                        name, category, description, params, is_enabled,
                        role, signal_group, ai_rating
                    )
                    VALUES (
                        :name, :category, :description, :params, false,
                        :role, :signal_group, :ai_rating
                    )
                    ON CONFLICT (name) DO UPDATE SET
                        category = EXCLUDED.category,
                        description = EXCLUDED.description,
                        params = EXCLUDED.params,
                        role = EXCLUDED.role,
                        signal_group = EXCLUDED.signal_group,
                        ai_rating = EXCLUDED.ai_rating,
                        updated_at = NOW()
                """),
                row,
            )
        cleanup_stats = await _cleanup_obsolete_strategy_data(session, active_names)
        await session.commit()
        if cleanup_stats.get("strategies", 0) > 0:
            logger.info("[策略清理] 清理统计：%s", cleanup_stats)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import os

    setup_logging(settings.log_level)

    await init_redis()
    await _sync_strategies_to_db()
    # 缓存预热（受配置开关控制）
    if settings.cache_warmup_on_startup:
        redis = get_redis()
        if redis is not None:
            await warmup_cache(redis, async_session_factory)

    # 检查是否跳过数据完整性检查（支持环境变量）
    skip_integrity_check = os.getenv("SKIP_INTEGRITY_CHECK", "false").lower() in ("true", "1", "yes")
    await start_scheduler(skip_integrity_check=skip_integrity_check)

    # 启动实时监控
    from app.api.realtime import set_realtime_manager
    from app.api.websocket import set_redis_client, start_redis_listener, stop_redis_listener
    from app.data.tushare import TushareClient
    from app.realtime.manager import RealtimeManager

    redis = get_redis()
    realtime_mgr = None
    try:
        tushare_client = TushareClient()
        realtime_mgr = RealtimeManager(tushare_client, redis)
        set_realtime_manager(realtime_mgr)
        if redis:
            set_redis_client(redis)
            await start_redis_listener()
        await realtime_mgr.start()
        logger.info("[启动] 实时监控已启动")
    except Exception:
        logger.warning("[启动] 实时监控启动失败，跳过", exc_info=True)

    yield

    # 优雅关闭：停止实时监控
    if realtime_mgr:
        try:
            await realtime_mgr.stop()
        except Exception:
            logger.warning("[关闭] 实时监控停止失败", exc_info=True)
    try:
        await stop_redis_listener()
    except Exception:
        pass

    # 优雅关闭：等待运行中的任务完成
    await _graceful_shutdown()


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)

# CORS 配置（允许前端开发服务器跨域访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求性能监控中间件
app.add_middleware(RequestPerformanceMiddleware)

# 注册路由
app.include_router(health_router)
app.include_router(strategy_router)
app.include_router(backtest_router)
app.include_router(data_router)
app.include_router(ai_router)
app.include_router(optimization_router)
app.include_router(news_router)
app.include_router(alert_router)
app.include_router(realtime_router)
app.include_router(task_log_router)
app.include_router(ws_router)
app.include_router(v4backtest_router)
app.include_router(research_router)
