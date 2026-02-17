"""AI 分析结果 HTTP API。

提供 AI 分析结果查询端点。
"""

from datetime import date

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import text

from app.ai.manager import get_ai_manager
from app.database import async_session_factory

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


class AIAnalysisItemResponse(BaseModel):
    """单条 AI 分析结果。"""

    ts_code: str
    trade_date: str
    ai_score: int
    ai_signal: str
    ai_summary: str
    prompt_version: str
    token_usage: dict | None = None
    created_at: str | None = None


class AIAnalysisListResponse(BaseModel):
    """AI 分析结果列表响应。"""

    trade_date: str
    total: int
    results: list[AIAnalysisItemResponse]


@router.get("/analysis", response_model=AIAnalysisListResponse)
async def get_ai_analysis(
    date: date | None = Query(None, description="查询日期（默认最近有结果的日期）"),
) -> AIAnalysisListResponse:
    """查询指定日期的 AI 分析结果。"""
    target = date
    if target is None:
        # 查询最近有 AI 结果的日期
        async with async_session_factory() as session:
            result = await session.execute(
                text("SELECT MAX(trade_date) FROM ai_analysis_results")
            )
            target = result.scalar()
        if target is None:
            return AIAnalysisListResponse(trade_date="", total=0, results=[])

    ai_manager = get_ai_manager()
    results = await ai_manager.get_results(target, async_session_factory)

    return AIAnalysisListResponse(
        trade_date=target.isoformat(),
        total=len(results),
        results=[AIAnalysisItemResponse(**r) for r in results],
    )
