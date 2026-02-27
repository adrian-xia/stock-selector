"""策略引擎 HTTP API。

提供策略列表查询、参数元数据查询、选股执行和策略配置管理端点。
"""

import json
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
    industries: list[str] | None = Field(
        None, description="行业过滤（如 ['电子', '计算机']）"
    )
    markets: list[str] | None = Field(
        None, description="市场过滤（如 ['主板', '创业板']）"
    )


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
        industries=req.industries,
        markets=req.markets,
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


@router.get("/industries")
async def list_industries():
    """获取所有行业列表（去重）。"""
    async with async_session_factory() as session:
        result = await session.execute(
            text("SELECT DISTINCT industry FROM stocks WHERE list_status = 'L' AND industry IS NOT NULL ORDER BY industry")
        )
        return [row[0] for row in result.fetchall()]


@router.get("/markets")
async def list_markets():
    """获取所有市场列表。"""
    async with async_session_factory() as session:
        result = await session.execute(
            text("SELECT DISTINCT market FROM stocks WHERE list_status = 'L' AND market IS NOT NULL ORDER BY market")
        )
        return [row[0] for row in result.fetchall()]


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


# ---------------------------------------------------------------------------
# 策略配置管理端点
# ---------------------------------------------------------------------------

class StrategyConfigResponse(BaseModel):
    """单个策略的配置状态。"""

    name: str
    display_name: str
    category: str
    description: str
    default_params: dict
    params: dict
    is_enabled: bool


class StrategyConfigListResponse(BaseModel):
    """策略配置列表响应。"""

    strategies: list[StrategyConfigResponse]


class StrategyConfigUpdateRequest(BaseModel):
    """更新单个策略配置的请求。"""

    is_enabled: bool | None = None
    params: dict | None = None


class StrategyConfigBatchItem(BaseModel):
    """批量更新中的单个策略配置。"""

    name: str
    is_enabled: bool | None = None
    params: dict | None = None


class StrategyConfigBatchRequest(BaseModel):
    """批量更新策略配置的请求。"""

    strategies: list[StrategyConfigBatchItem] = Field(..., min_length=1)


@router.get("/config", response_model=StrategyConfigListResponse)
async def get_strategy_config() -> StrategyConfigListResponse:
    """获取所有策略的配置状态（is_enabled + params）。"""
    # 从 DB 读取配置
    async with async_session_factory() as session:
        result = await session.execute(
            text("SELECT name, is_enabled, params FROM strategies")
        )
        db_rows = {row[0]: (row[1], row[2]) for row in result.fetchall()}

    # 合并内存注册表的元数据和 DB 的配置
    configs: list[StrategyConfigResponse] = []
    for meta in StrategyFactory.get_all():
        is_enabled = False
        params: dict = {}
        if meta.name in db_rows:
            is_enabled = db_rows[meta.name][0]
            params_raw = db_rows[meta.name][1]
            if params_raw:
                try:
                    params = json.loads(params_raw) if isinstance(params_raw, str) else params_raw
                except (json.JSONDecodeError, TypeError):
                    params = {}

        configs.append(StrategyConfigResponse(
            name=meta.name,
            display_name=meta.display_name,
            category=meta.category,
            description=meta.description,
            default_params=meta.default_params,
            params=params,
            is_enabled=is_enabled,
        ))

    return StrategyConfigListResponse(strategies=configs)


@router.put("/config/batch")
async def batch_update_strategy_config(req: StrategyConfigBatchRequest) -> dict:
    """批量更新策略配置（一次性启用/禁用多个）。"""
    # 校验所有策略名称
    available = {m.name for m in StrategyFactory.get_all()}
    invalid = [item.name for item in req.strategies if item.name not in available]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"未知策略：{invalid}",
        )

    async with async_session_factory() as session:
        for item in req.strategies:
            set_parts: list[str] = ["updated_at = NOW()"]
            params: dict = {"name": item.name}

            if item.is_enabled is not None:
                set_parts.append("is_enabled = :is_enabled")
                params["is_enabled"] = item.is_enabled
            if item.params is not None:
                set_parts.append("params = :params")
                params["params"] = json.dumps(item.params)

            await session.execute(
                text(f"UPDATE strategies SET {', '.join(set_parts)} WHERE name = :name"),
                params,
            )
        await session.commit()

    return {"updated": len(req.strategies)}


@router.put("/config/{name}", response_model=StrategyConfigResponse)
async def update_strategy_config(
    name: str, req: StrategyConfigUpdateRequest
) -> StrategyConfigResponse:
    """更新单个策略的 is_enabled 和 params。"""
    # 校验策略存在
    try:
        meta = StrategyFactory.get_meta(name)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"策略 '{name}' 不存在")

    async with async_session_factory() as session:
        # 构建动态 SET 子句
        set_parts: list[str] = ["updated_at = NOW()"]
        params: dict = {"name": name}

        if req.is_enabled is not None:
            set_parts.append("is_enabled = :is_enabled")
            params["is_enabled"] = req.is_enabled
        if req.params is not None:
            set_parts.append("params = :params")
            params["params"] = json.dumps(req.params)

        await session.execute(
            text(f"UPDATE strategies SET {', '.join(set_parts)} WHERE name = :name"),
            params,
        )
        await session.commit()

        # 读取更新后的配置
        result = await session.execute(
            text("SELECT is_enabled, params FROM strategies WHERE name = :name"),
            {"name": name},
        )
        row = result.fetchone()

    is_enabled = row[0] if row else False
    current_params: dict = {}
    if row and row[1]:
        try:
            current_params = json.loads(row[1]) if isinstance(row[1], str) else row[1]
        except (json.JSONDecodeError, TypeError):
            current_params = {}

    return StrategyConfigResponse(
        name=meta.name,
        display_name=meta.display_name,
        category=meta.category,
        description=meta.description,
        default_params=meta.default_params,
        params=current_params,
        is_enabled=is_enabled,
    )


# ---------------------------------------------------------------------------
# 命中率追踪端点
# ---------------------------------------------------------------------------

class HitStatResponse(BaseModel):
    """单条命中率统计记录。"""
    strategy_name: str
    stat_date: date
    period: str
    total_picks: int
    win_count: int
    hit_rate: float | None
    avg_return: float | None
    median_return: float | None
    best_return: float | None
    worst_return: float | None


class PickHistoryResponse(BaseModel):
    """单条历史选股记录。"""
    id: int
    strategy_name: str
    pick_date: date
    ts_code: str
    pick_score: float | None
    pick_close: float | None
    return_1d: float | None
    return_3d: float | None
    return_5d: float | None
    return_10d: float | None
    return_20d: float | None
    max_return: float | None
    max_drawdown: float | None


@router.get("/hit-stats", response_model=list[HitStatResponse])
async def get_hit_stats(
    strategy_name: str | None = Query(None, description="策略名称，不传则返回所有策略"),
) -> list[HitStatResponse]:
    """获取策略命中率统计。

    返回每个策略最新一次统计日期的各周期命中率数据。
    """
    async with async_session_factory() as session:
        if strategy_name:
            result = await session.execute(
                text("""
                    SELECT strategy_name, stat_date, period, total_picks, win_count,
                           hit_rate, avg_return, median_return, best_return, worst_return
                    FROM strategy_hit_stats
                    WHERE strategy_name = :name
                      AND stat_date = (
                          SELECT MAX(stat_date) FROM strategy_hit_stats
                          WHERE strategy_name = :name
                      )
                    ORDER BY period
                """),
                {"name": strategy_name},
            )
        else:
            result = await session.execute(
                text("""
                    SELECT s.strategy_name, s.stat_date, s.period, s.total_picks, s.win_count,
                           s.hit_rate, s.avg_return, s.median_return, s.best_return, s.worst_return
                    FROM strategy_hit_stats s
                    INNER JOIN (
                        SELECT strategy_name, MAX(stat_date) AS max_date
                        FROM strategy_hit_stats
                        GROUP BY strategy_name
                    ) latest ON s.strategy_name = latest.strategy_name
                           AND s.stat_date = latest.max_date
                    ORDER BY s.strategy_name, s.period
                """)
            )
        rows = result.fetchall()

    return [
        HitStatResponse(
            strategy_name=r[0],
            stat_date=r[1],
            period=r[2],
            total_picks=r[3],
            win_count=r[4],
            hit_rate=float(r[5]) if r[5] is not None else None,
            avg_return=float(r[6]) if r[6] is not None else None,
            median_return=float(r[7]) if r[7] is not None else None,
            best_return=float(r[8]) if r[8] is not None else None,
            worst_return=float(r[9]) if r[9] is not None else None,
        )
        for r in rows
    ]


@router.get("/picks/history", response_model=list[PickHistoryResponse])
async def get_pick_history(
    strategy_name: str = Query(..., description="策略名称"),
    days: int = Query(30, ge=1, le=365, description="查询最近 N 个交易日"),
) -> list[PickHistoryResponse]:
    """获取策略历史选股记录。

    返回指定策略最近 N 个交易日的选股记录，包含收益回填数据。
    """
    async with async_session_factory() as session:
        result = await session.execute(
            text("""
                SELECT id, strategy_name, pick_date, ts_code, pick_score, pick_close,
                       return_1d, return_3d, return_5d, return_10d, return_20d,
                       max_return, max_drawdown
                FROM strategy_picks
                WHERE strategy_name = :strategy_name
                  AND pick_date >= (
                      SELECT cal_date FROM trade_calendar
                      WHERE is_open = true AND cal_date <= CURRENT_DATE
                      ORDER BY cal_date DESC
                      OFFSET :offset LIMIT 1
                  )
                ORDER BY pick_date DESC, ts_code
            """),
            {"strategy_name": strategy_name, "offset": days - 1},
        )
        rows = result.fetchall()

    def _f(v) -> float | None:
        return float(v) if v is not None else None

    return [
        PickHistoryResponse(
            id=r[0],
            strategy_name=r[1],
            pick_date=r[2],
            ts_code=r[3],
            pick_score=_f(r[4]),
            pick_close=_f(r[5]),
            return_1d=_f(r[6]),
            return_3d=_f(r[7]),
            return_5d=_f(r[8]),
            return_10d=_f(r[9]),
            return_20d=_f(r[10]),
            max_return=_f(r[11]),
            max_drawdown=_f(r[12]),
        )
        for r in rows
    ]


# ---------------------------------------------------------------------------
# 交易计划端点
# ---------------------------------------------------------------------------

class TradePlanResponse(BaseModel):
    """单条交易计划响应。"""
    id: int
    ts_code: str
    plan_date: date
    valid_date: date
    direction: str
    trigger_type: str
    trigger_condition: str
    trigger_price: float | None
    stop_loss: float | None
    take_profit: float | None
    risk_reward_ratio: float | None
    source_strategy: str
    confidence: float | None
    triggered: bool | None
    actual_price: float | None


@router.post("/plan/generate")
async def generate_trade_plan(target_date: date | None = None) -> dict:
    """生成交易计划。基于最新选股结果。"""
    import json as _json
    from app.strategy.trade_plan import TradePlanGenerator

    # 确定目标日期
    target = target_date
    if target is None:
        async with async_session_factory() as session:
            row = await session.execute(
                text("SELECT MAX(trade_date) FROM stock_daily WHERE vol > 0")
            )
            target = row.scalar()
        if target is None:
            raise HTTPException(status_code=400, detail="数据库中无日线数据")

    # 读取启用的策略
    async with async_session_factory() as session:
        result = await session.execute(
            text("SELECT name, params FROM strategies WHERE is_enabled = true")
        )
        rows = result.fetchall()

    if not rows:
        raise HTTPException(status_code=400, detail="没有启用的策略")

    strategy_names = []
    strategy_params: dict[str, dict] = {}
    for name, params_raw in rows:
        strategy_names.append(name)
        if params_raw:
            try:
                p = _json.loads(params_raw) if isinstance(params_raw, str) else params_raw
                if p:
                    strategy_params[name] = p
            except (ValueError, TypeError):
                pass

    # 执行选股
    from app.strategy.pipeline import execute_pipeline
    pipeline_result = await execute_pipeline(
        session_factory=async_session_factory,
        strategy_names=strategy_names,
        target_date=target,
        top_n=50,
        strategy_params=strategy_params or None,
    )

    if not pipeline_result.picks:
        return {"target_date": str(target), "generated": 0, "message": "选股结果为空"}

    # 生成交易计划
    generator = TradePlanGenerator()
    plans = await generator.generate(async_session_factory, pipeline_result.picks, target)

    return {
        "target_date": str(target),
        "generated": len(plans),
        "picks": len(pipeline_result.picks),
    }


@router.get("/plan/latest", response_model=list[TradePlanResponse])
async def get_latest_plan(limit: int = Query(20, ge=1, le=200)) -> list[TradePlanResponse]:
    """获取最新交易计划。"""
    async with async_session_factory() as session:
        result = await session.execute(
            text("""
                SELECT id, ts_code, plan_date, valid_date,
                       direction, trigger_type, trigger_condition, trigger_price,
                       stop_loss, take_profit, risk_reward_ratio,
                       source_strategy, confidence, triggered, actual_price
                FROM trade_plans
                WHERE plan_date = (SELECT MAX(plan_date) FROM trade_plans)
                ORDER BY id
                LIMIT :limit
            """),
            {"limit": limit},
        )
        rows = result.fetchall()

    def _f(v) -> float | None:
        return float(v) if v is not None else None

    return [
        TradePlanResponse(
            id=r[0], ts_code=r[1], plan_date=r[2], valid_date=r[3],
            direction=r[4], trigger_type=r[5], trigger_condition=r[6],
            trigger_price=_f(r[7]), stop_loss=_f(r[8]), take_profit=_f(r[9]),
            risk_reward_ratio=_f(r[10]), source_strategy=r[11],
            confidence=_f(r[12]), triggered=r[13], actual_price=_f(r[14]),
        )
        for r in rows
    ]


@router.get("/plan/history", response_model=list[TradePlanResponse])
async def get_plan_history(
    ts_code: str | None = Query(None, description="股票代码，不传则返回所有"),
    days: int = Query(7, ge=1, le=90, description="查询最近 N 天"),
) -> list[TradePlanResponse]:
    """获取历史交易计划。"""
    async with async_session_factory() as session:
        if ts_code:
            result = await session.execute(
                text("""
                    SELECT id, ts_code, plan_date, valid_date,
                           direction, trigger_type, trigger_condition, trigger_price,
                           stop_loss, take_profit, risk_reward_ratio,
                           source_strategy, confidence, triggered, actual_price
                    FROM trade_plans
                    WHERE ts_code = :ts_code
                      AND plan_date >= CURRENT_DATE - :days * INTERVAL '1 day'
                    ORDER BY plan_date DESC, id
                """),
                {"ts_code": ts_code, "days": days},
            )
        else:
            result = await session.execute(
                text("""
                    SELECT id, ts_code, plan_date, valid_date,
                           direction, trigger_type, trigger_condition, trigger_price,
                           stop_loss, take_profit, risk_reward_ratio,
                           source_strategy, confidence, triggered, actual_price
                    FROM trade_plans
                    WHERE plan_date >= CURRENT_DATE - :days * INTERVAL '1 day'
                    ORDER BY plan_date DESC, id
                """),
                {"days": days},
            )
        rows = result.fetchall()

    def _f(v) -> float | None:
        return float(v) if v is not None else None

    return [
        TradePlanResponse(
            id=r[0], ts_code=r[1], plan_date=r[2], valid_date=r[3],
            direction=r[4], trigger_type=r[5], trigger_condition=r[6],
            trigger_price=_f(r[7]), stop_loss=_f(r[8]), take_profit=_f(r[9]),
            risk_reward_ratio=_f(r[10]), source_strategy=r[11],
            confidence=_f(r[12]), triggered=r[13], actual_price=_f(r[14]),
        )
        for r in rows
    ]
