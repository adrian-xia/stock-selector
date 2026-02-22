"""任务执行日志查询 API。

提供任务执行历史的查询接口，支持按任务名、状态、日期过滤。
"""

import logging
from datetime import date
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import text

from app.config import settings
from app.database import async_session_factory

logger = logging.getLogger(__name__)

router = APIRouter(prefix=settings.api_prefix, tags=["task-log"])


class TaskLogEntry(BaseModel):
    """任务执行日志条目。"""
    id: int
    task_name: str
    status: str
    started_at: str
    finished_at: str | None = None
    duration_seconds: float | None = None
    result_summary: dict[str, Any] | None = None
    error_message: str | None = None
    trade_date: str | None = None


class TaskLogListResponse(BaseModel):
    """任务日志列表响应。"""
    total: int
    items: list[TaskLogEntry]


@router.get("/tasks/logs", response_model=TaskLogListResponse)
async def list_task_logs(
    task_name: str | None = Query(None, description="按任务名过滤"),
    status: str | None = Query(None, description="按状态过滤（running/success/failed）"),
    trade_date: date | None = Query(None, description="按交易日过滤"),
    limit: int = Query(50, ge=1, le=200, description="返回条数"),
    offset: int = Query(0, ge=0, description="分页偏移"),
) -> Any:
    """查询任务执行历史。"""
    # 构建动态 WHERE 条件
    conditions = []
    params: dict[str, Any] = {"limit": limit, "offset": offset}

    if task_name:
        conditions.append("task_name = :task_name")
        params["task_name"] = task_name
    if status:
        conditions.append("status = :status")
        params["status"] = status
    if trade_date:
        conditions.append("trade_date = :trade_date")
        params["trade_date"] = trade_date

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    async with async_session_factory() as session:
        # 查询总数
        count_result = await session.execute(
            text(f"SELECT COUNT(*) FROM task_execution_log WHERE {where_clause}"),
            params,
        )
        total = count_result.scalar_one()

        # 查询数据
        result = await session.execute(
            text(
                f"SELECT id, task_name, status, started_at, finished_at, "
                f"duration_seconds, result_summary, error_message, trade_date "
                f"FROM task_execution_log WHERE {where_clause} "
                f"ORDER BY started_at DESC LIMIT :limit OFFSET :offset"
            ),
            params,
        )
        rows = result.fetchall()

    items = [
        TaskLogEntry(
            id=row[0],
            task_name=row[1],
            status=row[2],
            started_at=row[3].isoformat() if row[3] else None,
            finished_at=row[4].isoformat() if row[4] else None,
            duration_seconds=float(row[5]) if row[5] is not None else None,
            result_summary=row[6],
            error_message=row[7],
            trade_date=row[8].isoformat() if row[8] else None,
        )
        for row in rows
    ]

    return TaskLogListResponse(total=total, items=items)
