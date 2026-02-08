"""均线多头排列策略。

逻辑：MA5 > MA10 > MA20 > MA60，表示强势上涨趋势。
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategy


class MALongArrangeStrategy(BaseStrategy):
    """均线多头排列策略：短期均线依次高于长期均线。"""

    name = "ma-long-arrange"
    display_name = "均线多头排列"
    category = "technical"
    description = "MA5 > MA10 > MA20 > MA60，强势上涨趋势"
    default_params = {}

    async def filter_batch(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        """检测均线多头排列。"""
        ma5 = df.get("ma5", pd.Series(dtype=float)).fillna(0)
        ma10 = df.get("ma10", pd.Series(dtype=float)).fillna(0)
        ma20 = df.get("ma20", pd.Series(dtype=float)).fillna(0)
        ma60 = df.get("ma60", pd.Series(dtype=float)).fillna(0)

        # 多头排列：MA5 > MA10 > MA20 > MA60，且 MA60 > 0（有效值）
        signal = (ma5 > ma10) & (ma10 > ma20) & (ma20 > ma60) & (ma60 > 0)
        trading = df.get("vol", pd.Series(dtype=float)).fillna(0) > 0

        return signal & trading
