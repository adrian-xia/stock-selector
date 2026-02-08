"""Phase 4.1 手动验证回测收益计算准确性。

随机选择10只股票进行回测，并对其中一只进行详细的手动验证：
1. 获取实际交易记录
2. 手动计算每笔交易的盈亏和佣金
3. 对比回测引擎的计算结果
"""

import asyncio
import logging
from datetime import date
from decimal import Decimal

from app.backtest.engine import run_backtest
from app.database import async_session_factory
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# 随机选择的10只股票（排除指数）
TEST_STOCKS = [
    ("001206.SZ", "依依股份"),
    ("603209.SH", "兴通股份"),
    ("603321.SH", "梅轮电梯"),
    ("300639.SZ", "凯普生物"),
    ("600929.SH", "雪天盐业"),
    ("002813.SZ", "路畅科技"),
    ("601997.SH", "贵阳银行"),
    ("600633.SH", "浙数文化"),
    ("000713.SZ", "国投丰乐"),
    ("002607.SZ", "中公教育"),
]


async def manual_verify_trades(code: str, trades: list[dict], final_value: float) -> dict:
    """手动验证交易记录的准确性。

    对每笔交易进行手动计算：
    1. 佣金计算（买入万2.5，卖出万2.5+印花税千1）
    2. 最终净值验证（初始资金 + 所有交易盈亏）
    """
    if not trades:
        return {
            "verified": True,
            "issues": [],
            "manual_final_value": 1_000_000.0,
            "value_diff": 0.0,
            "value_diff_pct": 0.0,
            "total_trades": 0,
            "buy_count": 0,
            "sell_count": 0,
        }

    issues = []
    buy_trades = [t for t in trades if t["direction"] == "buy"]
    sell_trades = [t for t in trades if t["direction"] == "sell"]

    # 验证买入佣金
    for trade in buy_trades:
        turnover = trade["price"] * trade["size"]
        expected_comm = max(turnover * 0.00025, 5.0)
        actual_comm = trade["commission"]

        if abs(actual_comm - expected_comm) > 1.0:
            issues.append({
                "type": "买入佣金异常",
                "trade": trade,
                "expected": round(expected_comm, 2),
                "actual": actual_comm,
                "diff": round(abs(actual_comm - expected_comm), 2),
            })

    # 验证卖出佣金
    for sell_trade in sell_trades:
        turnover = sell_trade["price"] * sell_trade["size"]
        # 佣金 = 万2.5 + 印花税千1
        expected_comm = max(turnover * 0.00025, 5.0) + turnover * 0.001
        actual_comm = sell_trade["commission"]

        if abs(actual_comm - expected_comm) > 1.0:
            issues.append({
                "type": "卖出佣金异常",
                "trade": sell_trade,
                "expected": round(expected_comm, 2),
                "actual": actual_comm,
                "diff": round(abs(actual_comm - expected_comm), 2),
            })

    # 手动计算总盈亏和最终净值
    total_pnl = 0
    for i in range(min(len(buy_trades), len(sell_trades))):
        buy = buy_trades[i]
        sell = sell_trades[i]
        gross_pnl = (sell["price"] - buy["price"]) * sell["size"]
        net_pnl = gross_pnl - buy["commission"] - sell["commission"]
        total_pnl += net_pnl

    manual_final_value = 1_000_000.0 + total_pnl

    # 验证最终净值（允许 0.1% 的误差）
    value_diff = abs(manual_final_value - final_value)
    value_diff_pct = value_diff / final_value * 100

    if value_diff_pct > 0.1:
        issues.append({
            "type": "最终净值异常",
            "manual_value": round(manual_final_value, 2),
            "actual_value": round(final_value, 2),
            "diff": round(value_diff, 2),
            "diff_pct": round(value_diff_pct, 4),
        })

    return {
        "verified": len(issues) == 0,
        "issues": issues,
        "total_trades": len(trades),
        "buy_count": len(buy_trades),
        "sell_count": len(sell_trades),
        "manual_final_value": round(manual_final_value, 2),
        "value_diff": round(value_diff, 2),
        "value_diff_pct": round(value_diff_pct, 4),
    }


async def run_single_backtest(code: str, name: str) -> dict | None:
    """对单只股票执行回测。"""
    try:
        result = await run_backtest(
            session_factory=async_session_factory,
            stock_codes=[code],
            strategy_name="ma-cross",
            strategy_params={"hold_days": 10, "stop_loss_pct": 0.05},
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            initial_capital=1_000_000.0,
        )

        strat = result["strategy_instance"]
        trades = result["trades_log"]
        equity = result["equity_curve"]

        # 提取绩效
        final_value = strat.broker.getvalue()
        total_return = (final_value - 1_000_000.0) / 1_000_000.0 * 100

        # 手动验证交易
        verification = await manual_verify_trades(code, trades, final_value)

        return {
            "code": code,
            "name": name,
            "final_value": round(final_value, 2),
            "total_return_pct": round(total_return, 2),
            "total_trades": len(trades),
            "equity_points": len(equity),
            "elapsed_ms": result["elapsed_ms"],
            "verification": verification,
            "trades": trades,
        }
    except Exception as e:
        logger.error("回测失败 %s (%s): %s", code, name, e)
        return None


async def main() -> None:
    logger.info("=" * 80)
    logger.info("Phase 4.1 手动验证回测收益计算准确性")
    logger.info("=" * 80)

    results = []
    for code, name in TEST_STOCKS:
        logger.info("\n--- %s (%s) ---", code, name)

        result = await run_single_backtest(code, name)
        if result:
            results.append(result)
            logger.info("  最终净值: %.2f", result["final_value"])
            logger.info("  总收益率: %.2f%%", result["total_return_pct"])
            logger.info("  交易次数: %d", result["total_trades"])
            logger.info("  耗时: %d ms", result["elapsed_ms"])

            verification = result["verification"]
            if verification["verified"]:
                logger.info("  ✓ 手动验证通过（净值差异: %.2f, %.4f%%）",
                           verification["value_diff"], verification["value_diff_pct"])
            else:
                logger.warning("  ⚠️  验证失败: %d 个问题", len(verification["issues"]))
                for issue in verification["issues"][:3]:
                    logger.warning("    %s", issue)

    # 详细验证第一只有交易的股票
    logger.info("\n" + "=" * 80)
    logger.info("详细手动验证")
    logger.info("=" * 80)

    for result in results:
        if result["total_trades"] > 0:
            logger.info("\n选择 %s (%s) 进行详细验证", result["code"], result["name"])
            logger.info("总交易数: %d", result["total_trades"])

            trades = result["trades"]
            logger.info("\n交易明细:")
            for i, trade in enumerate(trades[:10], 1):  # 只显示前10笔
                logger.info("  %d. %s %s股 @ %.2f, 佣金=%.2f, 盈亏=%.2f",
                           i, trade["direction"], trade["size"], trade["price"],
                           trade["commission"], trade["pnl"])

            if len(trades) > 10:
                logger.info("  ... (共 %d 笔交易)", len(trades))

            # 手动计算总收益
            buy_trades = [t for t in trades if t["direction"] == "buy"]
            sell_trades = [t for t in trades if t["direction"] == "sell"]

            total_pnl = 0
            for i in range(min(len(buy_trades), len(sell_trades))):
                buy = buy_trades[i]
                sell = sell_trades[i]
                gross_pnl = (sell["price"] - buy["price"]) * sell["size"]
                net_pnl = gross_pnl - buy["commission"] - sell["commission"]
                total_pnl += net_pnl

            logger.info("\n手动计算:")
            logger.info("  买入次数: %d", len(buy_trades))
            logger.info("  卖出次数: %d", len(sell_trades))
            logger.info("  总盈亏: %.2f", total_pnl)
            logger.info("  手动计算最终净值: %.2f", 1_000_000.0 + total_pnl)
            logger.info("  回测最终净值: %.2f", result["final_value"])
            logger.info("  差异: %.2f (%.4f%%)",
                       abs((1_000_000.0 + total_pnl) - result["final_value"]),
                       abs((1_000_000.0 + total_pnl) - result["final_value"]) / result["final_value"] * 100)
            logger.info("  收益率: %.2f%%", result["total_return_pct"])

            break

    # 汇总统计
    logger.info("\n" + "=" * 80)
    logger.info("汇总统计")
    logger.info("=" * 80)
    logger.info("成功回测: %d / %d", len(results), len(TEST_STOCKS))

    if results:
        avg_return = sum(r["total_return_pct"] for r in results) / len(results)
        total_trades = sum(r["total_trades"] for r in results)
        verified_ok = sum(1 for r in results if r["verification"]["verified"])

        logger.info("平均收益率: %.2f%%", avg_return)
        logger.info("总交易次数: %d", total_trades)
        logger.info("手动验证通过: %d / %d", verified_ok, len(results))

        # 收益率分布
        positive = sum(1 for r in results if r["total_return_pct"] > 0)
        logger.info("盈利股票: %d / %d (%.1f%%)",
                   positive, len(results), positive / len(results) * 100)

    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
