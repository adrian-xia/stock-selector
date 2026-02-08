"""验证复权因子正确性和回测前复权效果。

任务 5.2：对有除权除息的股票执行回测，确认价格连续性和收益计算正确。
"""

import asyncio
import logging
import sys

import pandas as pd
from sqlalchemy import text

from app.database import async_session_factory

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


async def verify_adj_factor(ts_code: str) -> None:
    """验证指定股票的前复权价格连续性。"""
    async with async_session_factory() as session:
        result = await session.execute(
            text("""
                SELECT trade_date, open, high, low, close, adj_factor
                FROM stock_daily
                WHERE ts_code = :ts_code AND adj_factor IS NOT NULL
                ORDER BY trade_date ASC
            """),
            {"ts_code": ts_code},
        )
        rows = result.fetchall()

    if not rows:
        logger.error("股票 %s 无 adj_factor 数据", ts_code)
        return

    columns = ["trade_date", "open", "high", "low", "close", "adj_factor"]
    df = pd.DataFrame(rows, columns=columns)
    for col in ["open", "high", "low", "close", "adj_factor"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    logger.info("=" * 60)
    logger.info("股票: %s  数据量: %d 条", ts_code, len(df))
    logger.info("日期范围: %s ~ %s", df["trade_date"].iloc[0], df["trade_date"].iloc[-1])
    logger.info("=" * 60)

    # --- 1. 不复权价格：检查除权日跳空 ---
    df["raw_pct"] = df["close"].pct_change() * 100
    # 找除权日（adj_factor 变化的日期）
    df["adj_changed"] = df["adj_factor"] != df["adj_factor"].shift(1)
    ex_dates = df[df["adj_changed"] & df.index > 0]

    logger.info("\n[不复权] 除权日价格跳变:")
    for _, row in ex_dates.iterrows():
        logger.info(
            "  %s  adj: %.6f -> %.6f  收盘: %.2f  涨跌: %+.2f%%",
            row["trade_date"], df.loc[_ - 1, "adj_factor"] if _ > 0 else 0,
            row["adj_factor"], row["close"], row["raw_pct"],
        )

    # --- 2. 前复权价格：验证连续性 ---
    latest_adj = df["adj_factor"].iloc[-1]
    adj_ratio = df["adj_factor"] / latest_adj
    df["adj_close"] = df["close"] * adj_ratio
    df["adj_pct"] = df["adj_close"].pct_change() * 100

    # 在除权日，前复权后的涨跌幅应该是合理的（不会有大跳空）
    logger.info("\n[前复权] 除权日价格连续性:")
    all_ok = True
    for _, row in ex_dates.iterrows():
        adj_pct = df.loc[_, "adj_pct"]
        adj_close = df.loc[_, "adj_close"]
        prev_adj_close = df.loc[_ - 1, "adj_close"] if _ > 0 else 0
        # 除权日前复权涨跌幅应在 -11% ~ +11% 之间（涨跌停范围）
        ok = -11 <= adj_pct <= 11
        status = "OK" if ok else "WARN"
        if not ok:
            all_ok = False
        logger.info(
            "  %s  前复权收盘: %.2f -> %.2f  涨跌: %+.2f%%  [%s]",
            row["trade_date"], prev_adj_close, adj_close, adj_pct, status,
        )

    # --- 3. 全局统计：前复权后异常涨跌幅 ---
    # 排除首日，检查是否有超过 ±22%（ST 涨跌停 5% + 正常 10% 的极端情况）
    extreme = df[(df["adj_pct"].abs() > 22) & (df.index > 0)]
    logger.info("\n[前复权] 异常涨跌幅 (>±22%%): %d 条", len(extreme))
    if not extreme.empty:
        for _, row in extreme.head(10).iterrows():
            logger.info(
                "  %s  前复权收盘: %.2f  涨跌: %+.2f%%",
                row["trade_date"], row["adj_close"], row["adj_pct"],
            )

    # --- 4. 总结 ---
    logger.info("\n" + "=" * 60)
    if all_ok and extreme.empty:
        logger.info("结论: 前复权价格连续性验证通过 ✓")
    else:
        logger.info("结论: 存在异常，需要进一步检查")
    logger.info("=" * 60)


async def main() -> None:
    # 验证股票列表（PLAN 中指定的 + 已有数据的）
    codes = sys.argv[1:] if len(sys.argv) > 1 else ["600519.SH"]
    for code in codes:
        await verify_adj_factor(code)
        print()


if __name__ == "__main__":
    asyncio.run(main())
