from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.database import engine
from app.logger import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.log_level)
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok"}
