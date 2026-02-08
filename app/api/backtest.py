"""回测引擎 HTTP API。

提供回测执行和结果查询端点。
"""

import json
import logging
from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.backtest.engine import run_backtest
from app.backtest.writer import BacktestResultWriter
from app.database import async_session_factory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/backtest", tags=["backtest"])


# ---------------------------------------------------------------------------
# Pydantic 请求/响应模型
# ---------------------------------------------------------------------------

class BacktestRunRequest(BaseModel):
    """回测执行请求。"""

    strategy_name: str = Field(..., description="策略名称")
    strategy_params: dict = Field(default_factory=dict, description="策略参数覆盖")
    stock_codes: list[str] = Field(..., min_length=1, description="股票代码列表")
    start_date: date = Field(..., description="回测开始日期")
    end_date: date = Field(..., description="回测结束日期")
    initial_capital: float = Field(
        1_000_000.0, gt=0, description="初始资金（元）"
    )


class BacktestMetrics(BaseModel):
    """回测绩效指标。"""

    total_return: float | None = None
    annual_return: float | None = None
    max_drawdown: float | None = None
    sharpe_ratio: float | None = None
    win_rate: float | None = None
    profit_loss_ratio: float | None = None
    total_trades: int = 0
    calmar_ratio: float | None = None
    sortino_ratio: float | None = None
    volatility: float | None = None
    elapsed_ms: int = 0


class BacktestRunResponse(BaseModel):
    """回测执行响应。"""

    task_id: int
    status: str
    result: BacktestMetrics | None = None
    error_message: str | None = None


class TradeEntry(BaseModel):
    """单笔交易记录。"""

    stock_code: str
    direction: str
    date: str
    price: float
    size: int
    commission: float
    pnl: float


class EquityCurveEntry(BaseModel):
    """净值曲线数据点。"""

    date: str
    value: float


class BacktestListItem(BaseModel):
    """回测任务列表项。"""

    task_id: int
    strategy_name: str
    stock_count: int
    start_date: date | None = None
    end_date: date | None = None
    status: str
    annual_return: float | None = None
    created_at: str


class BacktestListResponse(BaseModel):
    """回测任务列表响应。"""

    total: int
    page: int
    page_size: int
    items: list[BacktestListItem]


class BacktestResultResponse(BaseModel):
    """回测结果详情响应。"""

    task_id: int
    status: str
    strategy_name: str | None = None
    stock_codes: list[str] | None = None
    start_date: date | None = None
    end_date: date | None = None
    result: BacktestMetrics | None = None
    trades: list[TradeEntry] | None = None
    equity_curve: list[EquityCurveEntry] | None = None
    error_message: str | None = None


# ---------------------------------------------------------------------------
# 端点
# ---------------------------------------------------------------------------

@router.post("/run", response_model=BacktestRunResponse)
async def run_backtest_api(req: BacktestRunRequest) -> BacktestRunResponse:
    """执行回测并同步返回结果。

    流程：校验参数 → 创建 task 记录 → 执行回测 → 写入结果 → 返回响应
    """
    # 校验日期范围
    if req.start_date >= req.end_date:
        raise HTTPException(
            status_code=400,
            detail=f"开始日期 {req.start_date} 必须早于结束日期 {req.end_date}",
        )

    writer = BacktestResultWriter(async_session_factory)

    # 创建 task 记录
    async with async_session_factory() as session:
        # 查找策略 ID
        strategy_row = await session.execute(
            text("SELECT id FROM strategies WHERE name = :name"),
            {"name": req.strategy_name},
        )
        strategy_id = strategy_row.scalar_one_or_none()
        if strategy_id is None:
            raise HTTPException(
                status_code=400,
                detail=f"未知策略: {req.strategy_name}",
            )

        result = await session.execute(
            text("""
                INSERT INTO backtest_tasks (
                    strategy_id, strategy_params, stock_codes,
                    start_date, end_date, initial_capital, status
                ) VALUES (
                    :strategy_id, CAST(:strategy_params AS jsonb),
                    CAST(:stock_codes AS jsonb),
                    :start_date, :end_date, :initial_capital, 'pending'
                )
                RETURNING id
            """),
            {
                "strategy_id": strategy_id,
                "strategy_params": json.dumps(req.strategy_params),
                "stock_codes": json.dumps(req.stock_codes),
                "start_date": req.start_date,
                "end_date": req.end_date,
                "initial_capital": req.initial_capital,
            },
        )
        task_id = result.scalar_one()
        # 更新状态为 running
        await session.execute(
            text("""
                UPDATE backtest_tasks
                SET status = 'running', updated_at = NOW()
                WHERE id = :task_id
            """),
            {"task_id": task_id},
        )
        await session.commit()

    # PLACEHOLDER_ENDPOINT_CONTINUE

    # 执行回测
    try:
        bt_result = await run_backtest(
            session_factory=async_session_factory,
            stock_codes=req.stock_codes,
            strategy_name=req.strategy_name,
            strategy_params=req.strategy_params,
            start_date=req.start_date,
            end_date=req.end_date,
            initial_capital=req.initial_capital,
        )

        # 写入结果
        await writer.save(
            task_id=task_id,
            strat=bt_result["strategy_instance"],
            equity_curve=bt_result["equity_curve"],
            trades_log=bt_result["trades_log"],
            initial_capital=req.initial_capital,
            elapsed_ms=bt_result["elapsed_ms"],
        )

        # 查询保存的结果构建响应
        async with async_session_factory() as session:
            row = await session.execute(
                text(
                    "SELECT * FROM backtest_results WHERE task_id = :tid"
                ),
                {"tid": task_id},
            )
            res = row.mappings().first()

        metrics = BacktestMetrics(
            total_return=res["total_return"] if res else None,
            annual_return=res["annual_return"] if res else None,
            max_drawdown=res["max_drawdown"] if res else None,
            sharpe_ratio=res["sharpe_ratio"] if res else None,
            win_rate=res["win_rate"] if res else None,
            profit_loss_ratio=res["profit_loss_ratio"] if res else None,
            total_trades=res["total_trades"] if res else 0,
            calmar_ratio=res["calmar_ratio"] if res else None,
            sortino_ratio=res["sortino_ratio"] if res else None,
            volatility=res["volatility"] if res else None,
            elapsed_ms=bt_result["elapsed_ms"],
        )

        return BacktestRunResponse(
            task_id=task_id,
            status="completed",
            result=metrics,
        )

    except Exception as e:
        logger.exception("回测执行失败：task_id=%d", task_id)
        await writer.mark_failed(task_id, str(e))
        return BacktestRunResponse(
            task_id=task_id,
            status="failed",
            error_message=str(e),
        )

@router.get("/result/{task_id}", response_model=BacktestResultResponse)
async def get_backtest_result(task_id: int) -> BacktestResultResponse:
    """查询回测结果（含交易明细和净值曲线）。"""
    async with async_session_factory() as session:
        # 查询 task
        task_row = await session.execute(
            text("""
                SELECT t.*, COALESCE(s.name, '') AS strategy_name
                FROM backtest_tasks t
                LEFT JOIN strategies s ON t.strategy_id = s.id
                WHERE t.id = :tid
            """),
            {"tid": task_id},
        )
        task = task_row.mappings().first()

    if not task:
        raise HTTPException(status_code=404, detail=f"回测任务 {task_id} 不存在")

    status = task["status"]

    # 如果任务还在运行中，返回 running 状态
    if status in ("pending", "running"):
        return BacktestResultResponse(
            task_id=task_id,
            status=status,
            strategy_name=task["strategy_name"],
        )

    # 如果任务失败，返回错误信息
    if status == "failed":
        return BacktestResultResponse(
            task_id=task_id,
            status="failed",
            strategy_name=task["strategy_name"],
            error_message=task.get("error_message"),
        )

    # 查询结果
    async with async_session_factory() as session:
        res_row = await session.execute(
            text("SELECT * FROM backtest_results WHERE task_id = :tid"),
            {"tid": task_id},
        )
        res = res_row.mappings().first()

    # 解析 stock_codes（JSONB 字段）
    stock_codes = task.get("stock_codes")
    if isinstance(stock_codes, str):
        stock_codes = json.loads(stock_codes)

    metrics = None
    trades = None
    equity_curve = None

    if res:
        metrics = BacktestMetrics(
            total_return=res["total_return"],
            annual_return=res["annual_return"],
            max_drawdown=res["max_drawdown"],
            sharpe_ratio=res["sharpe_ratio"],
            win_rate=res["win_rate"],
            profit_loss_ratio=res["profit_loss_ratio"],
            total_trades=res["total_trades"],
            calmar_ratio=res["calmar_ratio"],
            sortino_ratio=res["sortino_ratio"],
            volatility=res["volatility"],
        )

        # 解析 trades_json
        trades_data = res.get("trades_json")
        if trades_data:
            if isinstance(trades_data, str):
                trades_data = json.loads(trades_data)
            trades = [TradeEntry(**t) for t in trades_data]

        # 解析 equity_curve_json
        ec_data = res.get("equity_curve_json")
        if ec_data:
            if isinstance(ec_data, str):
                ec_data = json.loads(ec_data)
            equity_curve = [EquityCurveEntry(**e) for e in ec_data]

    return BacktestResultResponse(
        task_id=task_id,
        status=status,
        strategy_name=task["strategy_name"],
        stock_codes=stock_codes,
        start_date=task.get("start_date"),
        end_date=task.get("end_date"),
        result=metrics,
        trades=trades,
        equity_curve=equity_curve,
    )


@router.get("/list", response_model=BacktestListResponse)
async def list_backtest_tasks(
    page: int = 1,
    page_size: int = 20,
) -> BacktestListResponse:
    """分页查询回测任务列表，按创建时间倒序。"""
    page_size = min(page_size, 100)
    offset = (page - 1) * page_size

    async with async_session_factory() as session:
        # 查询总数
        count_row = await session.execute(
            text("SELECT COUNT(*) FROM backtest_tasks")
        )
        total = count_row.scalar_one()

        # 分页查询，LEFT JOIN 获取策略名称和年化收益率
        rows = await session.execute(
            text("""
                SELECT t.id, COALESCE(s.name, '') AS strategy_name,
                       t.stock_codes, t.start_date,
                       t.end_date, t.status, t.created_at,
                       r.annual_return
                FROM backtest_tasks t
                LEFT JOIN strategies s ON t.strategy_id = s.id
                LEFT JOIN backtest_results r ON t.id = r.task_id
                ORDER BY t.created_at DESC
                LIMIT :limit OFFSET :offset
            """),
            {"limit": page_size, "offset": offset},
        )
        tasks = rows.mappings().all()

    items = []
    for t in tasks:
        stock_codes = t["stock_codes"]
        if isinstance(stock_codes, str):
            stock_codes = json.loads(stock_codes)
        stock_count = len(stock_codes) if stock_codes else 0

        items.append(BacktestListItem(
            task_id=t["id"],
            strategy_name=t["strategy_name"],
            stock_count=stock_count,
            start_date=t["start_date"],
            end_date=t["end_date"],
            status=t["status"],
            annual_return=float(t["annual_return"]) if t["annual_return"] is not None else None,
            created_at=str(t["created_at"]),
        ))

    return BacktestListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )
