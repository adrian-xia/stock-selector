from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.backtest import router as backtest_router
from app.api.strategy import router as strategy_router
from app.config import settings
from app.database import engine
from app.logger import setup_logging
from app.scheduler.core import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.log_level)
    await start_scheduler()
    yield
    await stop_scheduler()
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)

# 注册路由
app.include_router(strategy_router)
app.include_router(backtest_router)


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok"}
