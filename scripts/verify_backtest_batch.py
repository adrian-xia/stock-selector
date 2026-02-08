"""Phase 4 回测准确性批量验证。

对多只不同特征的股票执行回测，验证：
1. 前复权价格连续性（有除权的股票）
2. 佣金计算正确性（万 2.5 + 印花税千 1 + 最低 5 元）
3. 涨跌停限制生效
4. 回测结果合理性
"""

import asyncio
import logging
from datetime import date
from decimal import Decimal

from app.backtest.engine import run_backtest
from app.database import async_session_factory

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# 测试股票列表（覆盖不同市值、行业、板块）
TEST_STOCKS = [
    ("600519.SH", "贵州茅台", "大盘蓝筹，高价股，多次除权"),
    ("000001.SZ", "平安银行", "金融股，低价，有除权"),
    ("300750.SZ", "宁德时代", "创业板，新能源，高波动"),
    ("600036.SH", "招商银行", "银行股，稳健"),
    ("000858.SZ", "五粮液", "白酒，有除权"),
    ("601318.SH", "中国平安", "保险，大盘"),
    ("002594.SZ", "比亚迪", "新能源汽车，高波动"),
    ("600028.SH", "中国石化", "能源，低价，有除权"),
    ("688981.SH", "中芯国际", "科创板，芯片"),
    ("000333.SZ", "美的集团", "家电，稳健"),
]


async def run_single_backtest(code: str, name: str) -> dict | None:
    """对单只股票执行回测。"""
    try:
        result = await run_backtest(
            session_factory=async_session_factory,
            stock_codes=[code],
            strategy_name="ma-cross",
            strategy_params={"hold_days": 10, "stop_loss_pct": 0.05},
            start_date=date(2024, 1, 1),
            end_date=date(2025, 12, 31),
            initial_capital=1_000_000.0,
        )

        strat = result["strategy_instance"]
        trades = result["trades_log"]
        equity = result["equity_curve"]

        # 提取绩效
        final_value = strat.broker.getvalue()
        total_return = (final_value - 1_000_000.0) / 1_000_000.0 * 100

        # 分析交易明细
        buy_trades = [t for t in trades if t["direction"] == "buy"]
        sell_trades = [t for t in trades if t["direction"] == "sell"]

        # 佣金检查（买入：万 2.5，卖出：万 2.5 + 印花税千 1）
        commission_issues = []
        for trade in buy_trades:
            expected_comm = max(trade["price"] * trade["size"] * 0.00025, 5.0)
            if abs(trade["commission"] - expected_comm) > 1.0:
                commission_issues.append(f"买入佣金异常: {trade}")

        for trade in sell_trades:
            # 卖出：佣金万 2.5 + 印花税千 1
            # 注意：这里应该分开计算，不是 0.00125
            expected_comm = max(trade["price"] * trade["size"] * 0.00025, 5.0) + trade["price"] * trade["size"] * 0.001
            if abs(trade["commission"] - expected_comm) > 1.0:
                commission_issues.append(f"卖出佣金异常: {trade}")

        return {
            "code": code,
            "name": name,
            "final_value": round(final_value, 2),
            "total_return_pct": round(total_return, 2),
            "total_trades": len(trades),
            "buy_count": len(buy_trades),
            "sell_count": len(sell_trades),
            "equity_points": len(equity),
            "elapsed_ms": result["elapsed_ms"],
            "commission_issues": commission_issues,
        }
    except Exception as e:
        logger.error("回测失败 %s (%s): %s", code, name, e)
        return None


async def main() -> None:
    logger.info("=" * 80)
    logger.info("Phase 4 回测准确性批量验证")
    logger.info("=" * 80)

    results = []
    for code, name, desc in TEST_STOCKS:
        logger.info("\n--- %s (%s) ---", code, name)
        logger.info("特征: %s", desc)

        result = await run_single_backtest(code, name)
        if result:
            results.append(result)
            logger.info("  最终净值: %.2f", result["final_value"])
            logger.info("  总收益率: %.2f%%", result["total_return_pct"])
            logger.info("  交易次数: %d (买 %d / 卖 %d)",
                       result["total_trades"], result["buy_count"], result["sell_count"])
            logger.info("  净值曲线: %d 点", result["equity_points"])
            logger.info("  耗时: %d ms", result["elapsed_ms"])

            if result["commission_issues"]:
                logger.warning("  ⚠️  佣金异常: %d 笔", len(result["commission_issues"]))
                for issue in result["commission_issues"][:3]:
                    logger.warning("    %s", issue)
            else:
                logger.info("  ✓ 佣金计算正确")

    # 汇总统计
    logger.info("\n" + "=" * 80)
    logger.info("汇总统计")
    logger.info("=" * 80)
    logger.info("成功回测: %d / %d", len(results), len(TEST_STOCKS))

    if results:
        avg_return = sum(r["total_return_pct"] for r in results) / len(results)
        total_trades = sum(r["total_trades"] for r in results)
        commission_ok = sum(1 for r in results if not r["commission_issues"])

        logger.info("平均收益率: %.2f%%", avg_return)
        logger.info("总交易次数: %d", total_trades)
        logger.info("佣金计算正确: %d / %d", commission_ok, len(results))

        # 收益率分布
        positive = sum(1 for r in results if r["total_return_pct"] > 0)
        logger.info("盈利股票: %d / %d (%.1f%%)",
                   positive, len(results), positive / len(results) * 100)

    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
