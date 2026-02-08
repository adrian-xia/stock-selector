"""布林带突破策略。

逻辑：价格从布林带下轨下方回升到下轨上方。
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategy


class BollBreakthroughStrategy(BaseStrategy):
    """布林带突破策略：价格从下轨下方回升。"""

    name = "boll-breakthrough"
    display_name = "布林带突破"
    category = "technical"
    description = "价格从布林带下轨下方回升，发出超跌反弹信号"
    default_params = {}

    async def filter_batch(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        """检测布林带下轨突破信号。"""
        prev_close = df.get("close_prev", pd.Series(dtype=float)).fillna(0)
        prev_lower = df.get("boll_lower_prev", pd.Series(dtype=float)).fillna(0)
        cur_close = df.get("close", pd.Series(dtype=float)).fillna(0)
        cur_lower = df.get("boll_lower", pd.Series(dtype=float)).fillna(0)

        # 昨日收盘 <= 下轨，今日收盘 > 下轨
        signal = (prev_close <= prev_lower) & (cur_close > cur_lower)
        trading = df.get("vol", pd.Series(dtype=float)).fillna(0) > 0

        return signal & trading
