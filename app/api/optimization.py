"""参数优化 HTTP API。

提供优化任务提交、进度查询、结果查询和参数空间查询端点。
"""

import asyncio
import json
import logging
from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.database import async_session_factory
from app.optimization.genetic import GeneticOptimizer
from app.optimization.grid_search import GridSearchOptimizer
from app.optimization.param_space import count_combinations
from app.strategy.factory import STRATEGY_REGISTRY, StrategyFactory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/optimization", tags=["optimization"])

# 最大网格搜索组合数限制
MAX_GRID_COMBINATIONS = 10000


# ---------------------------------------------------------------------------
# Pydantic 请求/响应模型
# ---------------------------------------------------------------------------

class OptimizationRunRequest(BaseModel):
    """优化任务提交请求。"""
    strategy_name: str = Field(..., description="策略名称")
    algorithm: str = Field(..., description="优化算法：grid 或 genetic")
    param_space: dict = Field(default_factory=dict, description="参数空间（覆盖策略默认）")
    stock_codes: list[str] = Field(..., min_length=1, description="股票代码列表")
    start_date: date = Field(..., description="回测开始日期")
    end_date: date = Field(..., description="回测结束日期")
    initial_capital: float = Field(1_000_000.0, gt=0, description="初始资金")
    ga_config: dict | None = Field(None, description="遗传算法超参数")
    top_n: int = Field(20, ge=1, le=100, description="保存前 N 个结果")


class OptimizationRunResponse(BaseModel):
    """优化任务提交响应。"""
    task_id: int
    status: str
    error_message: str | None = None


class OptimizationResultItem(BaseModel):
    """单个优化结果。"""
    rank: int
    params: dict
    sharpe_ratio: float | None = None
    annual_return: float | None = None
    max_drawdown: float | None = None
    win_rate: float | None = None
    total_trades: int | None = None
    total_return: float | None = None
    volatility: float | None = None
    calmar_ratio: float | None = None
    sortino_ratio: float | None = None


class OptimizationResultResponse(BaseModel):
    """优化结果详情响应。"""
    task_id: int
    status: str
    strategy_name: str | None = None
    algorithm: str | None = None
    progress: int = 0
    total_combinations: int | None = None
    completed_combinations: int = 0
    results: list[OptimizationResultItem] = []
    error_message: str | None = None


class OptimizationListItem(BaseModel):
    """优化任务列表项。"""
    task_id: int
    strategy_name: str
    algorithm: str
    status: str
    progress: int = 0
    total_combinations: int | None = None
    created_at: str


class OptimizationListResponse(BaseModel):
    """优化任务列表响应。"""
    total: int
    page: int
    page_size: int
    items: list[OptimizationListItem]


class ParamSpaceResponse(BaseModel):
    """参数空间响应。"""
    strategy_name: str
    display_name: str
    default_params: dict
    param_space: dict


# ---------------------------------------------------------------------------
# 端点
# ---------------------------------------------------------------------------

@router.post("/run", response_model=OptimizationRunResponse)
async def run_optimization(req: OptimizationRunRequest) -> OptimizationRunResponse:
    """提交参数优化任务并执行。"""
    # 校验策略
    if req.strategy_name not in STRATEGY_REGISTRY:
        raise HTTPException(status_code=400, detail=f"未知策略: {req.strategy_name}")

    if req.algorithm not in ("grid", "genetic"):
        raise HTTPException(status_code=400, detail="algorithm 必须为 grid 或 genetic")

    if req.start_date >= req.end_date:
        raise HTTPException(status_code=400, detail="开始日期必须早于结束日期")

    # 确定参数空间
    meta = StrategyFactory.get_meta(req.strategy_name)
    param_space = req.param_space if req.param_space else meta.param_space
    if not param_space:
        raise HTTPException(status_code=400, detail="该策略未定义参数空间，请手动指定 param_space")

    # 网格搜索组合数检查
    total_combos = count_combinations(param_space)
    if req.algorithm == "grid" and total_combos > MAX_GRID_COMBINATIONS:
        raise HTTPException(
            status_code=400,
            detail=f"网格搜索组合数 {total_combos} 超过上限 {MAX_GRID_COMBINATIONS}，建议使用遗传算法",
        )

    # 创建任务记录
    async with async_session_factory() as session:
        result = await session.execute(
            text("""
                INSERT INTO optimization_tasks (
                    strategy_name, algorithm, param_space, stock_codes,
                    start_date, end_date, initial_capital, ga_config, top_n,
                    status, total_combinations
                ) VALUES (
                    :strategy_name, :algorithm, CAST(:param_space AS jsonb),
                    CAST(:stock_codes AS jsonb),
                    :start_date, :end_date, :initial_capital,
                    CAST(:ga_config AS jsonb), :top_n,
                    'running', :total_combinations
                )
                RETURNING id
            """),
            {
                "strategy_name": req.strategy_name,
                "algorithm": req.algorithm,
                "param_space": json.dumps(param_space),
                "stock_codes": json.dumps(req.stock_codes),
                "start_date": req.start_date,
                "end_date": req.end_date,
                "initial_capital": req.initial_capital,
                "ga_config": json.dumps(req.ga_config) if req.ga_config else None,
                "top_n": req.top_n,
                "total_combinations": total_combos if req.algorithm == "grid" else None,
            },
        )
        task_id = result.scalar_one()
        await session.commit()

    # 后台执行优化
    asyncio.create_task(_run_optimization_task(
        task_id=task_id,
        strategy_name=req.strategy_name,
        algorithm=req.algorithm,
        param_space=param_space,
        stock_codes=req.stock_codes,
        start_date=req.start_date,
        end_date=req.end_date,
        initial_capital=req.initial_capital,
        ga_config=req.ga_config,
        top_n=req.top_n,
    ))

    return OptimizationRunResponse(task_id=task_id, status="running")


async def _run_optimization_task(
    task_id: int,
    strategy_name: str,
    algorithm: str,
    param_space: dict,
    stock_codes: list[str],
    start_date: date,
    end_date: date,
    initial_capital: float,
    ga_config: dict | None,
    top_n: int,
) -> None:
    """后台执行优化任务。"""
    try:
        # 进度回调：更新数据库
        async def _update_progress(completed: int, total: int) -> None:
            progress = int(completed / total * 100) if total > 0 else 0
            async with async_session_factory() as session:
                await session.execute(
                    text("""
                        UPDATE optimization_tasks
                        SET progress = :progress,
                            completed_combinations = :completed,
                            updated_at = NOW()
                        WHERE id = :task_id
                    """),
                    {"progress": progress, "completed": completed, "task_id": task_id},
                )
                await session.commit()

        # 同步包装的进度回调
        def progress_callback(completed: int, total: int) -> None:
            asyncio.create_task(_update_progress(completed, total))

        # 选择优化器并执行
        if algorithm == "grid":
            optimizer = GridSearchOptimizer(async_session_factory)
            results = await optimizer.optimize(
                strategy_name=strategy_name,
                param_space=param_space,
                stock_codes=stock_codes,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                progress_callback=progress_callback,
            )
        else:
            optimizer = GeneticOptimizer(async_session_factory)
            results = await optimizer.optimize(
                strategy_name=strategy_name,
                param_space=param_space,
                stock_codes=stock_codes,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                progress_callback=progress_callback,
                ga_config=ga_config,
            )

        # 保存 Top N 结果
        top_results = results[:top_n]
        async with async_session_factory() as session:
            for rank, r in enumerate(top_results, 1):
                await session.execute(
                    text("""
                        INSERT INTO optimization_results (
                            task_id, rank, params, sharpe_ratio, annual_return,
                            max_drawdown, win_rate, total_trades, total_return,
                            volatility, calmar_ratio, sortino_ratio
                        ) VALUES (
                            :task_id, :rank, CAST(:params AS jsonb),
                            :sharpe_ratio, :annual_return, :max_drawdown,
                            :win_rate, :total_trades, :total_return,
                            :volatility, :calmar_ratio, :sortino_ratio
                        )
                    """),
                    {
                        "task_id": task_id,
                        "rank": rank,
                        "params": json.dumps(r.params),
                        "sharpe_ratio": r.sharpe_ratio,
                        "annual_return": r.annual_return,
                        "max_drawdown": r.max_drawdown,
                        "win_rate": r.win_rate,
                        "total_trades": r.total_trades,
                        "total_return": r.total_return,
                        "volatility": r.volatility,
                        "calmar_ratio": r.calmar_ratio,
                        "sortino_ratio": r.sortino_ratio,
                    },
                )

            # 更新任务状态为完成
            await session.execute(
                text("""
                    UPDATE optimization_tasks
                    SET status = 'completed', progress = 100, updated_at = NOW()
                    WHERE id = :task_id
                """),
                {"task_id": task_id},
            )
            await session.commit()

        logger.info("优化任务 %d 完成，保存 %d 个结果", task_id, len(top_results))

    except Exception as e:
        logger.exception("优化任务 %d 执行失败", task_id)
        async with async_session_factory() as session:
            await session.execute(
                text("""
                    UPDATE optimization_tasks
                    SET status = 'failed', error_message = :error, updated_at = NOW()
                    WHERE id = :task_id
                """),
                {"task_id": task_id, "error": str(e)},
            )
            await session.commit()


@router.get("/result/{task_id}", response_model=OptimizationResultResponse)
async def get_optimization_result(task_id: int) -> OptimizationResultResponse:
    """查询优化结果。"""
    async with async_session_factory() as session:
        task_row = await session.execute(
            text("SELECT * FROM optimization_tasks WHERE id = :tid"),
            {"tid": task_id},
        )
        task = task_row.mappings().first()

    if not task:
        raise HTTPException(status_code=404, detail=f"优化任务 {task_id} 不存在")

    # 查询结果
    results_items: list[OptimizationResultItem] = []
    if task["status"] == "completed":
        async with async_session_factory() as session:
            res_rows = await session.execute(
                text("""
                    SELECT * FROM optimization_results
                    WHERE task_id = :tid ORDER BY rank
                """),
                {"tid": task_id},
            )
            for r in res_rows.mappings().all():
                params = r["params"]
                if isinstance(params, str):
                    params = json.loads(params)
                results_items.append(OptimizationResultItem(
                    rank=r["rank"],
                    params=params,
                    sharpe_ratio=float(r["sharpe_ratio"]) if r["sharpe_ratio"] is not None else None,
                    annual_return=float(r["annual_return"]) if r["annual_return"] is not None else None,
                    max_drawdown=float(r["max_drawdown"]) if r["max_drawdown"] is not None else None,
                    win_rate=float(r["win_rate"]) if r["win_rate"] is not None else None,
                    total_trades=r["total_trades"],
                    total_return=float(r["total_return"]) if r["total_return"] is not None else None,
                    volatility=float(r["volatility"]) if r["volatility"] is not None else None,
                    calmar_ratio=float(r["calmar_ratio"]) if r["calmar_ratio"] is not None else None,
                    sortino_ratio=float(r["sortino_ratio"]) if r["sortino_ratio"] is not None else None,
                ))

    return OptimizationResultResponse(
        task_id=task_id,
        status=task["status"],
        strategy_name=task["strategy_name"],
        algorithm=task["algorithm"],
        progress=task["progress"],
        total_combinations=task["total_combinations"],
        completed_combinations=task["completed_combinations"],
        results=results_items,
        error_message=task.get("error_message"),
    )


@router.get("/list", response_model=OptimizationListResponse)
async def list_optimization_tasks(
    page: int = 1,
    page_size: int = 20,
) -> OptimizationListResponse:
    """分页查询优化任务列表。"""
    page_size = min(page_size, 100)
    offset = (page - 1) * page_size

    async with async_session_factory() as session:
        count_row = await session.execute(
            text("SELECT COUNT(*) FROM optimization_tasks")
        )
        total = count_row.scalar_one()

        rows = await session.execute(
            text("""
                SELECT id, strategy_name, algorithm, status, progress,
                       total_combinations, created_at
                FROM optimization_tasks
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """),
            {"limit": page_size, "offset": offset},
        )
        tasks = rows.mappings().all()

    items = [
        OptimizationListItem(
            task_id=t["id"],
            strategy_name=t["strategy_name"],
            algorithm=t["algorithm"],
            status=t["status"],
            progress=t["progress"],
            total_combinations=t["total_combinations"],
            created_at=str(t["created_at"]),
        )
        for t in tasks
    ]

    return OptimizationListResponse(
        total=total, page=page, page_size=page_size, items=items,
    )


@router.get("/param-space/{strategy_name}", response_model=ParamSpaceResponse)
async def get_param_space(strategy_name: str) -> ParamSpaceResponse:
    """查询策略的参数空间定义。"""
    if strategy_name not in STRATEGY_REGISTRY:
        raise HTTPException(status_code=400, detail=f"未知策略: {strategy_name}")

    meta = StrategyFactory.get_meta(strategy_name)
    if not meta.param_space:
        raise HTTPException(status_code=404, detail=f"策略 {strategy_name} 未定义参数空间")

    return ParamSpaceResponse(
        strategy_name=meta.name,
        display_name=meta.display_name,
        default_params=meta.default_params,
        param_space=meta.param_space,
    )
