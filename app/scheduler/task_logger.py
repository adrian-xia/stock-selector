"""任务执行日志记录器。

将调度任务的执行状态（开始、成功、失败）持久化到 task_execution_log 表，
支持回溯排查任务执行历史。
"""

import logging
import time
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

logger = logging.getLogger(__name__)


class TaskLogger:
    """任务执行日志记录器。

    Usage:
        task_logger = TaskLogger(session_factory)

        # 方式 1：手动记录
        log_id = await task_logger.start("sync_raw_daily", trade_date=date.today())
        await task_logger.finish(log_id, status="success", result_summary={...})

        # 方式 2：上下文管理器（推荐）
        async with task_logger.track("sync_raw_daily", trade_date=date.today()) as ctx:
            # 执行任务...
            ctx["result"] = {"inserted": 5000}
    """

    def __init__(self, session_factory: async_sessionmaker):
        self._session_factory = session_factory

    async def start(
        self,
        task_name: str,
        trade_date: date | None = None,
    ) -> int:
        """记录任务开始，返回日志记录 ID。"""
        now = datetime.now(timezone.utc)
        async with self._session_factory() as session:
            result = await session.execute(
                text("""
                    INSERT INTO task_execution_log
                        (task_name, status, started_at, trade_date)
                    VALUES (:task_name, 'running', :started_at, :trade_date)
                    RETURNING id
                """),
                {
                    "task_name": task_name,
                    "started_at": now,
                    "trade_date": trade_date,
                },
            )
            log_id = result.scalar_one()
            await session.commit()

        logger.debug("[TaskLogger] 任务开始: %s (id=%d)", task_name, log_id)
        return log_id

    async def finish(
        self,
        log_id: int,
        status: str = "success",
        result_summary: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> None:
        """记录任务结束（成功或失败）。"""
        import json

        now = datetime.now(timezone.utc)
        async with self._session_factory() as session:
            await session.execute(
                text("""
                    UPDATE task_execution_log
                    SET status = :status,
                        finished_at = :finished_at,
                        duration_seconds = EXTRACT(EPOCH FROM (:finished_at - started_at)),
                        result_summary = :result_summary,
                        error_message = :error_message
                    WHERE id = :log_id
                """),
                {
                    "log_id": log_id,
                    "status": status,
                    "finished_at": now,
                    "result_summary": json.dumps(result_summary, default=str) if result_summary else None,
                    "error_message": error_message,
                },
            )
            await session.commit()

        logger.debug("[TaskLogger] 任务结束: id=%d status=%s", log_id, status)

    @asynccontextmanager
    async def track(
        self,
        task_name: str,
        trade_date: date | None = None,
    ):
        """任务执行跟踪上下文管理器。

        自动记录任务的开始、成功和失败。

        Usage:
            async with task_logger.track("post_market_pipeline", trade_date) as ctx:
                # 执行任务...
                ctx["result"] = {"steps_completed": 5}
        """
        ctx: dict[str, Any] = {"result": None}
        log_id = await self.start(task_name, trade_date)

        try:
            yield ctx
            await self.finish(
                log_id,
                status="success",
                result_summary=ctx.get("result"),
            )
        except Exception as e:
            await self.finish(
                log_id,
                status="failed",
                error_message=str(e),
            )
            raise
