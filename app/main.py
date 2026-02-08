from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.backtest import router as backtest_router
from app.api.data import router as data_router
from app.api.strategy import router as strategy_router
from app.cache.redis_client import close_redis, get_redis, init_redis
from app.cache.tech_cache import warmup_cache
from app.config import settings
from app.data.pool import close_pool, get_pool
from app.database import async_session_factory, engine
from app.logger import setup_logging
from app.scheduler.core import start_scheduler, stop_scheduler
from app.strategy.factory import StrategyFactory


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
    setup_logging(settings.log_level)
    await init_redis()
    get_pool()  # 初始化连接池
    await _sync_strategies_to_db()
    # 缓存预热（受配置开关控制）
    if settings.cache_warmup_on_startup:
        redis = get_redis()
        if redis is not None:
            await warmup_cache(redis, async_session_factory)
    await start_scheduler()
    yield
    await stop_scheduler()
    await close_pool()  # 关闭连接池
    await close_redis()
    await engine.dispose()


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


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok"}
