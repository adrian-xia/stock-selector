import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.ai import router as ai_router
from app.api.backtest import router as backtest_router
from app.api.data import router as data_router
from app.api.optimization import router as optimization_router
from app.api.strategy import router as strategy_router
from app.cache.redis_client import close_redis, get_redis, init_redis
from app.cache.tech_cache import warmup_cache
from app.config import settings
from app.database import async_session_factory, engine
from app.logger import setup_logging
from app.scheduler.core import start_scheduler, stop_scheduler
from app.strategy.factory import StrategyFactory

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


async def _sync_strategies_to_db() -> None:
    """将内存中注册的策略同步到 strategies 表（UPSERT）。"""
    from sqlalchemy import text

    all_meta = StrategyFactory.get_all()
    async with async_session_factory() as session:
        for meta in all_meta:
            await session.execute(
                text("""
                    INSERT INTO strategies (name, category, description, params)
                    VALUES (:name, :category, :description, :params)
                    ON CONFLICT (name) DO UPDATE SET
                        category = EXCLUDED.category,
                        description = EXCLUDED.description,
                        updated_at = NOW()
                """),
                {
                    "name": meta.name,
                    "category": meta.category,
                    "description": meta.description or "",
                    "params": "{}",
                },
            )
        await session.commit()


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

    yield

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

# 注册路由
app.include_router(strategy_router)
app.include_router(backtest_router)
app.include_router(data_router)
app.include_router(ai_router)
app.include_router(optimization_router)


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok"}
