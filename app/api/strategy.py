"""策略引擎 HTTP API。

提供策略列表查询、参数元数据查询和选股执行端点。
"""

from datetime import date

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.database import async_session_factory
from app.strategy.factory import StrategyFactory
from app.strategy.pipeline import execute_pipeline

router = APIRouter(prefix="/api/v1/strategy", tags=["strategy"])


# ---------------------------------------------------------------------------
# Pydantic 请求/响应模型
# ---------------------------------------------------------------------------

class StrategyRunRequest(BaseModel):
    """选股执行请求。"""

    strategy_names: list[str] = Field(
        ..., min_length=1, description="策略名称列表"
    )
    target_date: date | None = Field(
        None, description="筛选日期（默认最近交易日）"
    )
    base_filter: dict | None = Field(
        None, description="Layer 1 过滤参数覆盖"
    )
    top_n: int = Field(30, ge=1, le=200, description="返回数量上限")


class StockPickResponse(BaseModel):
    """单只股票选股结果。"""

    ts_code: str
    name: str
    close: float
    pct_chg: float
    matched_strategies: list[str]
    match_count: int
    ai_score: int | None = None
    ai_signal: str | None = None
    ai_summary: str | None = None


class StrategyRunResponse(BaseModel):
    """选股执行响应。"""

    target_date: date
    total_picks: int
    elapsed_ms: int
    layer_stats: dict[str, int]
    ai_enabled: bool = False
    picks: list[StockPickResponse]


class StrategyMetaResponse(BaseModel):
    """策略元数据响应。"""

    name: str
    display_name: str
    category: str
    description: str
    default_params: dict


class StrategyListResponse(BaseModel):
    """策略列表响应。"""

    strategies: list[StrategyMetaResponse]


class StrategySchemaResponse(BaseModel):
    """策略参数 schema 响应。"""

    name: str
    display_name: str
    default_params: dict


# ---------------------------------------------------------------------------
# 端点
# ---------------------------------------------------------------------------

@router.post("/run", response_model=StrategyRunResponse)
async def run_strategy(req: StrategyRunRequest) -> StrategyRunResponse:
    """执行选股策略管道。"""
    # 校验策略名称
    available = {m.name for m in StrategyFactory.get_all()}
    invalid = [n for n in req.strategy_names if n not in available]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"未知策略：{invalid}，可用策略：{sorted(available)}",
        )

    # 确定目标日期：优先使用用户指定日期，否则查询最近有数据的交易日
    target = req.target_date
    if target is None:
        async with async_session_factory() as session:
            latest = await session.execute(
                text("SELECT MAX(trade_date) FROM stock_daily WHERE vol > 0")
            )
            target = latest.scalar()
        if target is None:
            raise HTTPException(
                status_code=400,
                detail="数据库中无日线数据，请先执行数据同步",
            )

    result = await execute_pipeline(
        session_factory=async_session_factory,
        strategy_names=req.strategy_names,
        target_date=target,
        base_filter=req.base_filter,
        top_n=req.top_n,
    )

    return StrategyRunResponse(
        target_date=result.target_date,
        total_picks=len(result.picks),
        elapsed_ms=result.elapsed_ms,
        layer_stats=result.layer_stats,
        ai_enabled=result.ai_enabled,
        picks=[
            StockPickResponse(
                ts_code=p.ts_code,
                name=p.name,
                close=p.close,
                pct_chg=p.pct_chg,
                matched_strategies=p.matched_strategies,
                match_count=p.match_count,
                ai_score=p.ai_score,
                ai_signal=p.ai_signal,
                ai_summary=p.ai_summary,
            )
            for p in result.picks
        ],
    )


@router.get("/list", response_model=StrategyListResponse)
async def list_strategies(
    category: str | None = Query(None, description="按分类过滤：technical 或 fundamental"),
) -> StrategyListResponse:
    """获取可用策略列表。"""
    if category:
        metas = StrategyFactory.get_by_category(category)
    else:
        metas = StrategyFactory.get_all()

    return StrategyListResponse(
        strategies=[
            StrategyMetaResponse(
                name=m.name,
                display_name=m.display_name,
                category=m.category,
                description=m.description,
                default_params=m.default_params,
            )
            for m in metas
        ]
    )


@router.get("/schema/{name}", response_model=StrategySchemaResponse)
async def get_strategy_schema(name: str) -> StrategySchemaResponse:
    """获取指定策略的参数元数据。"""
    try:
        meta = StrategyFactory.get_meta(name)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"策略 '{name}' 不存在")

    return StrategySchemaResponse(
        name=meta.name,
        display_name=meta.display_name,
        default_params=meta.default_params,
    )
