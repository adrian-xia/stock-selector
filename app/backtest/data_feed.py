"""自定义 DataFeed 和数据加载。

PandasDataPlus 扩展 Backtrader 的 PandasData，添加换手率和复权因子。
load_stock_data() 从数据库加载日线数据并应用动态前复权。
"""

import logging
from datetime import date

import backtrader as bt
import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


class PandasDataPlus(bt.feeds.PandasData):
    """扩展的 Pandas DataFeed，增加 A 股特有字段。"""

    lines = ("turnover_rate", "adj_factor")

    params = (
        ("turnover_rate", -1),
        ("adj_factor", -1),
        ("datetime", None),
        ("open", "open"),
        ("high", "high"),
        ("low", "low"),
        ("close", "close"),
        ("volume", "vol"),
        ("openinterest", -1),
    )


async def load_stock_data(
    session: AsyncSession,
    ts_code: str,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """从数据库加载股票日线数据并应用动态前复权。

    前复权公式：price_adj = price_raw * (adj_factor / latest_adj_factor)

    Args:
        session: 异步数据库会话
        ts_code: 股票代码
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        包含前复权 OHLCV 数据的 DataFrame，按 trade_date 升序排列
    """
    sql = text("""
        SELECT
            trade_date, open, high, low, close, vol, amount,
            turnover_rate, adj_factor
        FROM stock_daily
        WHERE ts_code = :ts_code
          AND trade_date >= :start_date
          AND trade_date <= :end_date
        ORDER BY trade_date ASC
    """)

    result = await session.execute(sql, {
        "ts_code": ts_code,
        "start_date": start_date,
        "end_date": end_date,
    })
    rows = result.fetchall()

    if not rows:
        logger.warning("股票 %s 在 %s ~ %s 无数据", ts_code, start_date, end_date)
        return pd.DataFrame()

    columns = [
        "trade_date", "open", "high", "low", "close",
        "vol", "amount", "turnover_rate", "adj_factor",
    ]
    df = pd.DataFrame(rows, columns=columns)

    # 转换数值类型
    for col in ["open", "high", "low", "close", "vol", "amount", "turnover_rate", "adj_factor"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 动态前复权：price_adj = price_raw * (adj_factor / latest_adj_factor)
    latest_adj = df["adj_factor"].iloc[-1]
    if latest_adj and latest_adj > 0:
        adj_ratio = df["adj_factor"] / latest_adj
        for col in ["open", "high", "low", "close"]:
            df[col] = df[col] * adj_ratio

    # 设置日期索引（Backtrader 需要）
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = df.set_index("trade_date")

    logger.info("加载股票 %s 数据：%d 条（%s ~ %s）", ts_code, len(df), start_date, end_date)
    return df


def build_data_feed(
    df: pd.DataFrame,
    name: str = "",
) -> PandasDataPlus:
    """将 DataFrame 转换为 Backtrader DataFeed。

    Args:
        df: load_stock_data() 返回的 DataFrame
        name: DataFeed 名称（通常为股票代码）

    Returns:
        PandasDataPlus 实例
    """
    feed = PandasDataPlus(
        dataname=df,
        name=name,
        turnover_rate="turnover_rate",
        adj_factor="adj_factor",
    )
    return feed
