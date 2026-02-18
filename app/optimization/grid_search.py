"""网格搜索优化器：遍历参数空间所有组合。"""

import logging
from datetime import date

from app.backtest.engine import run_backtest
from app.optimization.base import BaseOptimizer, OptimizationResult, ProgressCallback
from app.optimization.param_space import generate_combinations

logger = logging.getLogger(__name__)


class GridSearchOptimizer(BaseOptimizer):
    """网格搜索优化器。

    遍历参数空间的所有组合，对每个组合执行回测，
    按 sharpe_ratio 降序排列返回结果。
    """

    async def optimize(
        self,
        strategy_name: str,
        param_space: dict,
        stock_codes: list[str],
        start_date: date,
        end_date: date,
        initial_capital: float = 1_000_000.0,
        progress_callback: ProgressCallback | None = None,
    ) -> list[OptimizationResult]:
        """执行网格搜索优化。"""
        combinations = generate_combinations(param_space)
        total = len(combinations)
        logger.info("网格搜索开始：策略=%s，总组合数=%d", strategy_name, total)

        results: list[OptimizationResult] = []

        for i, params in enumerate(combinations):
            try:
                bt_result = await run_backtest(
                    session_factory=self._session_factory,
                    stock_codes=stock_codes,
                    strategy_name=strategy_name,
                    strategy_params=params,
                    start_date=start_date,
                    end_date=end_date,
                    initial_capital=initial_capital,
                )
                opt_result = _extract_result(params, bt_result)
                results.append(opt_result)
            except Exception:
                logger.warning("参数组合 %s 回测失败，跳过", params, exc_info=True)

            if progress_callback:
                progress_callback(i + 1, total)

        # 按 sharpe_ratio 降序排列（None 排最后）
        results.sort(
            key=lambda r: r.sharpe_ratio if r.sharpe_ratio is not None else float("-inf"),
            reverse=True,
        )

        logger.info("网格搜索完成：有效结果 %d/%d", len(results), total)
        return results


def _extract_result(params: dict, bt_result: dict) -> OptimizationResult:
    """从回测结果中提取优化结果指标。"""
    strat = bt_result["strategy_instance"]

    # 从 Analyzers 提取指标
    sharpe = None
    max_dd = None
    win_rate = None
    total_trades = 0
    annual_return = None
    total_return = None
    volatility = None
    calmar = None
    sortino = None

    try:
        sharpe_analysis = strat.analyzers.sharpe.get_analysis()
        sharpe = sharpe_analysis.get("sharperatio")
    except Exception:
        pass

    try:
        dd_analysis = strat.analyzers.drawdown.get_analysis()
        max_dd = dd_analysis.get("max", {}).get("drawdown")
        if max_dd is not None:
            max_dd = -abs(max_dd) / 100  # 转为负数小数
    except Exception:
        pass

    try:
        trade_analysis = strat.analyzers.trades.get_analysis()
        total_trades = trade_analysis.get("total", {}).get("total", 0)
        won = trade_analysis.get("won", {}).get("total", 0)
        if total_trades > 0:
            win_rate = won / total_trades
    except Exception:
        pass

    try:
        returns_analysis = strat.analyzers.returns.get_analysis()
        annual_return = returns_analysis.get("rnorm100")
        if annual_return is not None:
            annual_return = annual_return / 100
    except Exception:
        pass

    # 从净值曲线计算总收益
    equity_curve = bt_result.get("equity_curve", [])
    if equity_curve and len(equity_curve) >= 2:
        initial = equity_curve[0].get("value", 1)
        final = equity_curve[-1].get("value", 1)
        if initial > 0:
            total_return = (final - initial) / initial

    return OptimizationResult(
        params=params,
        sharpe_ratio=sharpe,
        annual_return=annual_return,
        max_drawdown=max_dd,
        win_rate=win_rate,
        total_trades=total_trades,
        total_return=total_return,
        volatility=volatility,
        calmar_ratio=calmar,
        sortino_ratio=sortino,
    )
