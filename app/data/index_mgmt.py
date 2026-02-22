"""数据库索引生命周期管理模块。

全量导入时删除非主键索引以加速写入（3-5 倍提升），
导入完成后使用 CREATE INDEX CONCURRENTLY 重建索引。

仅在全量导入（init_data / backfill）场景使用，
日常增量同步不触发索引管理。
"""

import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


@dataclass
class IndexDefinition:
    """索引定义，用于删除后重建。"""
    name: str
    table_name: str
    definition: str  # 完整的 CREATE INDEX 语句


async def drop_indexes(engine: AsyncEngine, table_name: str) -> list[IndexDefinition]:
    """删除指定表的所有非主键索引，返回被删除索引的定义列表。

    Args:
        engine: SQLAlchemy async engine
        table_name: 目标表名

    Returns:
        被删除索引的定义列表（用于后续重建）
    """
    dropped: list[IndexDefinition] = []

    async with engine.begin() as conn:
        # 查询非主键索引的定义
        result = await conn.execute(text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = :table_name
              AND indexname NOT IN (
                  SELECT conindid::regclass::text
                  FROM pg_constraint
                  WHERE conrelid = :table_name::regclass
                    AND contype = 'p'
              )
        """), {"table_name": table_name})
        indexes = result.fetchall()

        for idx_name, idx_def in indexes:
            try:
                await conn.execute(text(f'DROP INDEX IF EXISTS "{idx_name}"'))
                dropped.append(IndexDefinition(
                    name=idx_name,
                    table_name=table_name,
                    definition=idx_def,
                ))
                logger.info("[索引管理] 已删除索引: %s (%s)", idx_name, table_name)
            except Exception as e:
                logger.error("[索引管理] 删除索引 %s 失败: %s", idx_name, e)

    if not dropped:
        logger.info("[索引管理] %s 无非主键索引需要删除", table_name)

    return dropped


async def rebuild_indexes(
    engine: AsyncEngine, index_definitions: list[IndexDefinition]
) -> list[str]:
    """根据索引定义列表重建索引。

    使用 CREATE INDEX CONCURRENTLY 避免锁表（需要在事务外执行）。

    Args:
        engine: SQLAlchemy async engine
        index_definitions: 待重建的索引定义列表

    Returns:
        重建失败的索引名列表
    """
    failed: list[str] = []

    for idx_def in index_definitions:
        start = time.monotonic()
        try:
            # CONCURRENTLY 不能在事务内执行，使用 raw connection
            async with engine.connect() as conn:
                await conn.execution_options(isolation_level="AUTOCOMMIT")
                # 将原始 CREATE INDEX 改为 CONCURRENTLY
                create_sql = idx_def.definition
                if "CONCURRENTLY" not in create_sql:
                    create_sql = create_sql.replace(
                        "CREATE INDEX", "CREATE INDEX CONCURRENTLY", 1
                    )
                # 加 IF NOT EXISTS 防止重复创建
                if "IF NOT EXISTS" not in create_sql:
                    create_sql = create_sql.replace(
                        "CONCURRENTLY", "CONCURRENTLY IF NOT EXISTS", 1
                    )
                await conn.execute(text(create_sql))

            elapsed = time.monotonic() - start
            logger.info(
                "[索引管理] 已重建索引: %s (%.1fs)", idx_def.name, elapsed
            )
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error(
                "[索引管理] 重建索引 %s 失败 (%.1fs): %s",
                idx_def.name, elapsed, e,
            )
            failed.append(idx_def.name)

    return failed


@asynccontextmanager
async def with_index_management(engine: AsyncEngine, table_names: list[str]):
    """全量导入索引管理上下文管理器。

    进入时删除指定表的非主键索引，退出时重建。

    Usage:
        async with with_index_management(engine, ["stock_daily", "technical_daily"]):
            # 执行大批量数据导入
            ...
    """
    start = time.monotonic()
    all_indexes: list[IndexDefinition] = []

    # 删除索引
    for table_name in table_names:
        indexes = await drop_indexes(engine, table_name)
        all_indexes.extend(indexes)

    logger.info(
        "[索引管理] 共删除 %d 个索引（%d 张表），开始导入...",
        len(all_indexes), len(table_names),
    )

    try:
        yield all_indexes
    finally:
        # 无论是否异常，都重建索引
        if all_indexes:
            logger.info("[索引管理] 开始重建 %d 个索引...", len(all_indexes))
            failed = await rebuild_indexes(engine, all_indexes)
            elapsed = time.monotonic() - start
            if failed:
                logger.warning(
                    "[索引管理] 索引管理完成 (%.1fs)，%d 个索引重建失败: %s",
                    elapsed, len(failed), failed,
                )
            else:
                logger.info(
                    "[索引管理] 索引管理完成 (%.1fs)，全部 %d 个索引已重建",
                    elapsed, len(all_indexes),
                )
