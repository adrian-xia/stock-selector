import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    echo=settings.db_echo,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional async database session."""
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


@asynccontextmanager
async def get_raw_connection():
    """获取底层 asyncpg 原始连接，用于 COPY 协议操作。

    通过 SQLAlchemy async engine 获取底层 asyncpg 连接，
    支持 copy_records_to_table() 等原生 asyncpg 方法。

    Usage:
        async with get_raw_connection() as raw_conn:
            await raw_conn.copy_records_to_table(...)
    """
    conn = await engine.raw_connection()
    try:
        # 获取底层 asyncpg 连接（剥离 SQLAlchemy 包装）
        raw_conn = conn.driver_connection
        yield raw_conn
    except Exception:
        logger.error("[get_raw_connection] COPY 操作异常，连接将被释放")
        raise
    finally:
        # 归还连接到连接池
        conn.close()


async def is_timescaledb_available(eng: AsyncEngine | None = None) -> bool:
    """检测当前 PostgreSQL 实例是否安装了 TimescaleDB 扩展。

    Args:
        eng: SQLAlchemy async engine，默认使用全局 engine

    Returns:
        True 如果 TimescaleDB 可用，否则 False
    """
    if eng is None:
        eng = engine
    try:
        async with eng.connect() as conn:
            result = await conn.execute(
                text("SELECT 1 FROM pg_available_extensions WHERE name = 'timescaledb'")
            )
            row = result.fetchone()
            if row:
                logger.info("[TimescaleDB] 扩展可用")
                return True
            else:
                logger.info("[TimescaleDB] 扩展不可用，将使用普通表")
                return False
    except Exception as e:
        logger.warning("[TimescaleDB] 检测失败，将使用普通表: %s", e)
        return False
