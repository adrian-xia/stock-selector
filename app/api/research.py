"""StarMap 盘后投研 API。

设计文档 §8：
- GET /research/overview — 投研总览
- GET /research/macro — 宏观信号明细
- GET /research/sectors — 行业共振排名
- GET /research/plans — 增强交易计划
"""

import logging
from datetime import date

from fastapi import APIRouter, Depends, Query

from app.database import async_session_factory
from app.research.repository.starmap_repo import StarMapRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/research", tags=["research"])


def _get_repo() -> StarMapRepository:
    return StarMapRepository(async_session_factory)


@router.get("/overview")
async def get_research_overview(
    trade_date: date = Query(..., description="交易日 YYYY-MM-DD"),
    repo: StarMapRepository = Depends(_get_repo),
):
    """盘后投研总览：宏观信号 + 行业共振 Top10 + 交易计划。"""
    return await repo.get_research_overview(trade_date)


@router.get("/macro")
async def get_macro_signal(
    trade_date: date = Query(..., description="交易日 YYYY-MM-DD"),
    repo: StarMapRepository = Depends(_get_repo),
):
    """宏观信号明细。"""
    signal = await repo.get_macro_signal(trade_date)
    if signal is None:
        return {"trade_date": trade_date.isoformat(), "data": None, "message": "未找到数据"}
    return {
        "trade_date": trade_date.isoformat(),
        "risk_appetite": signal.risk_appetite,
        "global_risk_score": float(signal.global_risk_score),
        "positive_sectors": signal.positive_sectors,
        "negative_sectors": signal.negative_sectors,
        "macro_summary": signal.macro_summary,
        "key_drivers": signal.key_drivers,
        "content_hash": signal.content_hash,
        "model_name": signal.model_name,
        "prompt_version": signal.prompt_version,
    }


@router.get("/sectors")
async def get_sector_resonance(
    trade_date: date = Query(..., description="交易日 YYYY-MM-DD"),
    limit: int = Query(20, ge=1, le=100),
    repo: StarMapRepository = Depends(_get_repo),
):
    """行业共振评分排名。"""
    sectors = await repo.get_sector_resonance(trade_date, top_n=limit)
    return {
        "trade_date": trade_date.isoformat(),
        "count": len(sectors),
        "sectors": [
            {
                "sector_code": s.sector_code,
                "sector_name": s.sector_name,
                "news_score": float(s.news_score),
                "moneyflow_score": float(s.moneyflow_score),
                "trend_score": float(s.trend_score),
                "final_score": float(s.final_score),
                "confidence": float(s.confidence),
                "drivers": s.drivers,
            }
            for s in sectors
        ],
    }


@router.get("/plans")
async def get_trade_plans(
    trade_date: date = Query(..., description="交易日 YYYY-MM-DD"),
    status: str | None = Query(None, description="计划状态过滤：PENDING/EXPIRED"),
    repo: StarMapRepository = Depends(_get_repo),
):
    """增强交易计划列表。"""
    plans = await repo.get_trade_plans(trade_date, status)
    return {
        "trade_date": trade_date.isoformat(),
        "count": len(plans),
        "plans": [
            {
                "ts_code": p.ts_code,
                "source_strategy": p.source_strategy,
                "plan_type": p.plan_type,
                "plan_status": p.plan_status,
                "entry_rule": p.entry_rule,
                "stop_loss_rule": p.stop_loss_rule,
                "take_profit_rule": p.take_profit_rule,
                "emergency_exit_text": p.emergency_exit_text,
                "position_suggestion": float(p.position_suggestion),
                "market_regime": p.market_regime,
                "market_risk_score": float(p.market_risk_score),
                "sector_name": p.sector_name,
                "sector_score": float(p.sector_score) if p.sector_score else None,
                "confidence": float(p.confidence),
                "reasoning": p.reasoning,
                "risk_flags": p.risk_flags,
            }
            for p in plans
        ],
    }
