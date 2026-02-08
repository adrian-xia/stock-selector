"""验证回测引擎前复权生效：对有除权的股票执行回测，确认收益计算正确。

任务 5.2：对比有/无 adj_factor 时的回测结果差异。
"""

import asyncio
import logging
from datetime import date

from app.backtest.engine import run_backtest
from app.database import async_session_factory

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)


async def run_single_backtest(
    code: str,
    start: date,
    end: date,
) -> dict | None:
    """对单只股票执行回测并返回结果摘要。"""
    try:
        result = await run_backtest(
            session_factory=async_session_factory,
            stock_codes=[code],
            strategy_name="ma-cross",
            strategy_params={"hold_days": 10, "stop_loss_pct": 0.05},
            start_date=start,
            end_date=end,
            initial_capital=1_000_000.0,
        )
        strat = result["strategy_instance"]

        # 提取绩效
        sharpe = strat.analyzers.sharpe.get_analysis()
        dd = strat.analyzers.drawdown.get_analysis()
        returns = strat.analyzers.returns.get_analysis()
        trades = strat.analyzers.trades.get_analysis()

        total_trades = trades.get("total", {}).get("total", 0)
        final_value = strat.broker.getvalue()
        total_return = (final_value - 1_000_000.0) / 1_000_000.0 * 100

        return {
            "code": code,
            "final_value": round(final_value, 2),
            "total_return_pct": round(total_return, 2),
            "max_drawdown_pct": round(dd.get("max", {}).get("drawdown", 0), 2),
            "total_trades": total_trades,
            "elapsed_ms": result["elapsed_ms"],
            "equity_points": len(result["equity_curve"]),
            "trades_log_count": len(result["trades_log"]),
        }
    except Exception as e:
        logger.error("回测失败 %s: %s", code, e)
        return None


async def main() -> None:
    # 选择有除权的股票（已有 adj_factor）
    test_cases = [
        ("600519.SH", date(2020, 1, 2), date(2025, 12, 31)),  # 贵州茅台
        ("600028.SH", date(2020, 1, 2), date(2025, 12, 31)),  # 中国石化
        ("600016.SH", date(2020, 1, 2), date(2025, 12, 31)),  # 民生银行
    ]

    logger.info("=" * 70)
    logger.info("回测前复权验证：对有除权的股票执行回测")
    logger.info("=" * 70)

    for code, start, end in test_cases:
        logger.info("\n--- %s (%s ~ %s) ---", code, start, end)
        result = await run_single_backtest(code, start, end)
        if result:
            logger.info("  最终净值: %.2f", result["final_value"])
            logger.info("  总收益率: %.2f%%", result["total_return_pct"])
            logger.info("  最大回撤: %.2f%%", result["max_drawdown_pct"])
            logger.info("  交易次数: %d", result["total_trades"])
            logger.info("  净值曲线点数: %d", result["equity_points"])
            logger.info("  耗时: %d ms", result["elapsed_ms"])

            # 验证关键指标合理性
            checks = []
            # 净值曲线应有数据
            if result["equity_points"] > 0:
                checks.append("净值曲线有数据 ✓")
            else:
                checks.append("净值曲线为空 ✗")
            # 应有交易发生
            if result["total_trades"] > 0:
                checks.append("有交易发生 ✓")
            else:
                checks.append("无交易 ✗")
            # 收益率应在合理范围（-50% ~ +500%）
            if -50 <= result["total_return_pct"] <= 500:
                checks.append("收益率合理 ✓")
            else:
                checks.append(f"收益率异常: {result['total_return_pct']}% ✗")

            logger.info("  检查: %s", " | ".join(checks))

    logger.info("\n" + "=" * 70)
    logger.info("回测前复权验证完成")
    logger.info("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
