"""回测结果提取与持久化。

从 Backtrader Analyzers 提取绩效指标，将交易明细和净值曲线
序列化为 JSON，写入 backtest_results 表。
"""

import logging
import math
from typing import Any

import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


def extract_metrics(strat: Any, initial_capital: float) -> dict[str, Any]:
    """从 Backtrader 策略实例的 Analyzers 提取绩效指标。

    Args:
        strat: 执行完毕的 Backtrader 策略实例
        initial_capital: 初始资金

    Returns:
        绩效指标字典
    """
    metrics: dict[str, Any] = {}

    # SharpeRatio
    try:
        sharpe_data = strat.analyzers.sharpe.get_analysis()
        metrics["sharpe_ratio"] = _safe_float(sharpe_data.get("sharperatio"))
    except Exception:
        metrics["sharpe_ratio"] = None

    # DrawDown
    try:
        dd_data = strat.analyzers.drawdown.get_analysis()
        max_dd = dd_data.get("max", {}).get("drawdown", 0)
        metrics["max_drawdown"] = round(float(max_dd) / 100, 4) if max_dd else 0.0
    except Exception:
        metrics["max_drawdown"] = None

    # Returns
    try:
        ret_data = strat.analyzers.returns.get_analysis()
        total_ret = ret_data.get("rtot", 0)
        annual_ret = ret_data.get("rnorm", 0)
        metrics["total_return"] = _safe_float(total_ret)
        metrics["annual_return"] = _safe_float(annual_ret)
    except Exception:
        metrics["total_return"] = None
        metrics["annual_return"] = None

    # TradeAnalyzer
    try:
        trade_data = strat.analyzers.trades.get_analysis()
        total_trades = trade_data.get("total", {}).get("total", 0)
        metrics["total_trades"] = int(total_trades) if total_trades else 0

        won = trade_data.get("won", {}).get("total", 0)
        lost = trade_data.get("lost", {}).get("total", 0)
        if total_trades and total_trades > 0:
            metrics["win_rate"] = round(float(won) / float(total_trades), 4)
        else:
            metrics["win_rate"] = None

        avg_won = trade_data.get("won", {}).get("pnl", {}).get("average", 0)
        avg_lost = trade_data.get("lost", {}).get("pnl", {}).get("average", 0)
        if avg_lost and abs(float(avg_lost)) > 0:
            metrics["profit_loss_ratio"] = round(
                abs(float(avg_won or 0)) / abs(float(avg_lost)), 4
            )
        else:
            metrics["profit_loss_ratio"] = None
    except Exception:
        metrics["total_trades"] = 0
        metrics["win_rate"] = None
        metrics["profit_loss_ratio"] = None

    return metrics


def calc_extra_metrics(
    equity_curve: list[dict],
    metrics: dict[str, Any],
) -> dict[str, Any]:
    """计算额外指标：calmar_ratio、volatility。

    Args:
        equity_curve: 净值曲线列表
        metrics: 已提取的基础指标

    Returns:
        更新后的指标字典
    """
    # Calmar Ratio = annual_return / max_drawdown
    annual_ret = metrics.get("annual_return") or 0
    max_dd = metrics.get("max_drawdown") or 0
    if max_dd > 0:
        metrics["calmar_ratio"] = round(float(annual_ret) / float(max_dd), 4)
    else:
        metrics["calmar_ratio"] = None

    # Volatility（年化日收益率标准差）
    if len(equity_curve) >= 2:
        values = [e["value"] for e in equity_curve]
        daily_returns = []
        for i in range(1, len(values)):
            if values[i - 1] > 0:
                daily_returns.append(values[i] / values[i - 1] - 1)
        if daily_returns:
            std = float(np.std(daily_returns, ddof=1))
            metrics["volatility"] = round(std * math.sqrt(252), 4)
        else:
            metrics["volatility"] = None
    else:
        metrics["volatility"] = None

    # Sortino Ratio（使用下行标准差）
    if len(equity_curve) >= 2:
        values = [e["value"] for e in equity_curve]
        daily_returns = []
        for i in range(1, len(values)):
            if values[i - 1] > 0:
                daily_returns.append(values[i] / values[i - 1] - 1)
        downside = [r for r in daily_returns if r < 0]
        if downside:
            downside_std = float(np.std(downside, ddof=1))
            if downside_std > 0:
                metrics["sortino_ratio"] = round(
                    float(annual_ret) / (downside_std * math.sqrt(252)), 4
                )
            else:
                metrics["sortino_ratio"] = None
        else:
            metrics["sortino_ratio"] = None
    else:
        metrics["sortino_ratio"] = None

    return metrics


class BacktestResultWriter:
    """回测结果写入器。"""

    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def save(
        self,
        task_id: int,
        strat: Any,
        equity_curve: list[dict],
        trades_log: list[dict],
        initial_capital: float,
        elapsed_ms: int,
    ) -> None:
        """保存回测结果到数据库。"""
        # 提取指标
        metrics = extract_metrics(strat, initial_capital)
        metrics = calc_extra_metrics(equity_curve, metrics)

        async with self._session_factory() as session:
            # 写入 backtest_results
            await session.execute(
                text("""
                    INSERT INTO backtest_results (
                        task_id, total_return, annual_return, max_drawdown,
                        sharpe_ratio, win_rate, profit_loss_ratio, total_trades,
                        calmar_ratio, sortino_ratio, volatility,
                        trades_json, equity_curve_json
                    ) VALUES (
                        :task_id, :total_return, :annual_return, :max_drawdown,
                        :sharpe_ratio, :win_rate, :profit_loss_ratio, :total_trades,
                        :calmar_ratio, :sortino_ratio, :volatility,
                        :trades_json::jsonb, :equity_curve_json::jsonb
                    )
                """),
                {
                    "task_id": task_id,
                    "total_return": metrics.get("total_return"),
                    "annual_return": metrics.get("annual_return"),
                    "max_drawdown": metrics.get("max_drawdown"),
                    "sharpe_ratio": metrics.get("sharpe_ratio"),
                    "win_rate": metrics.get("win_rate"),
                    "profit_loss_ratio": metrics.get("profit_loss_ratio"),
                    "total_trades": metrics.get("total_trades", 0),
                    "calmar_ratio": metrics.get("calmar_ratio"),
                    "sortino_ratio": metrics.get("sortino_ratio"),
                    "volatility": metrics.get("volatility"),
                    "trades_json": _to_json_str(trades_log),
                    "equity_curve_json": _to_json_str(equity_curve),
                },
            )

            # 更新任务状态为 completed
            await session.execute(
                text("""
                    UPDATE backtest_tasks
                    SET status = 'completed', updated_at = NOW()
                    WHERE id = :task_id
                """),
                {"task_id": task_id},
            )

            await session.commit()
            logger.info("回测结果已保存：task_id=%d", task_id)

    async def mark_failed(
        self,
        task_id: int,
        error_message: str,
    ) -> None:
        """标记回测任务失败。"""
        async with self._session_factory() as session:
            await session.execute(
                text("""
                    UPDATE backtest_tasks
                    SET status = 'failed', error_message = :error, updated_at = NOW()
                    WHERE id = :task_id
                """),
                {"task_id": task_id, "error": error_message},
            )
            await session.commit()
            logger.error("回测任务失败：task_id=%d, error=%s", task_id, error_message)


def _safe_float(val: Any) -> float | None:
    """安全转换为 float，None 和 NaN 返回 None。"""
    if val is None:
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f, 4)
    except (TypeError, ValueError):
        return None


def _to_json_str(data: list) -> str:
    """将列表序列化为 JSON 字符串。"""
    import json
    return json.dumps(data, ensure_ascii=False)
