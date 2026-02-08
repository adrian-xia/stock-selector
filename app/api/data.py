"""数据查询 HTTP API。

提供 K 线数据查询端点。
"""

from datetime import date

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import text

from app.database import async_session_factory

router = APIRouter(prefix="/api/v1/data", tags=["data"])


# ---------------------------------------------------------------------------
# Pydantic 响应模型
# ---------------------------------------------------------------------------

class KlineEntry(BaseModel):
    """单条 K 线数据。"""

    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class KlineResponse(BaseModel):
    """K 线查询响应。"""

    ts_code: str
    data: list[KlineEntry]


# ---------------------------------------------------------------------------
# 端点
# ---------------------------------------------------------------------------

@router.get("/kline/{ts_code}", response_model=KlineResponse)
async def get_kline(
    ts_code: str,
    start_date: date | None = Query(None, description="开始日期"),
    end_date: date | None = Query(None, description="结束日期"),
    limit: int = Query(120, ge=1, le=1000, description="返回条数上限"),
) -> KlineResponse:
    """查询指定股票的日 K 线数据（OHLCV）。"""
    # 构建查询条件
    conditions = ["ts_code = :ts_code"]
    params: dict = {"ts_code": ts_code, "limit": limit}

    if start_date:
        conditions.append("trade_date >= :start_date")
        params["start_date"] = start_date
    if end_date:
        conditions.append("trade_date <= :end_date")
        params["end_date"] = end_date

    where_clause = " AND ".join(conditions)

    async with async_session_factory() as session:
        result = await session.execute(
            text(f"""
                SELECT trade_date, open, high, low, close, vol
                FROM stock_daily
                WHERE {where_clause}
                ORDER BY trade_date DESC
                LIMIT :limit
            """),
            params,
        )
        rows = result.mappings().all()

    # 按日期升序返回
    data = [
        KlineEntry(
            date=str(row["trade_date"]),
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=float(row["vol"]),
        )
        for row in reversed(rows)
    ]

    return KlineResponse(ts_code=ts_code, data=data)
