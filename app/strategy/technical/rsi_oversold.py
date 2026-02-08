"""RSI 超卖反弹策略。

逻辑：RSI 从超卖区回升到反弹阈值以上。
默认参数：period=6, oversold=20, bounce=30
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategy


class RSIOversoldStrategy(BaseStrategy):
    """RSI 超卖反弹策略：RSI 从超卖区回升。"""

    name = "rsi-oversold"
    display_name = "RSI超卖反弹"
    category = "technical"
    description = "RSI 从超卖区域回升，发出反弹买入信号"
    default_params = {"period": 6, "oversold": 20, "bounce": 30}

    async def filter_batch(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        """检测 RSI 超卖反弹信号。"""
        period = self.params.get("period", 6)
        oversold = self.params.get("oversold", 20)
        bounce = self.params.get("bounce", 30)

        rsi_col = f"rsi{period}"
        prev_rsi_col = f"rsi{period}_prev"

        cur_rsi = df.get(rsi_col, pd.Series(dtype=float)).fillna(50)
        prev_rsi = df.get(prev_rsi_col, pd.Series(dtype=float)).fillna(50)

        # 昨日 RSI <= 超卖线，今日 RSI > 反弹线
        signal = (prev_rsi <= oversold) & (cur_rsi > bounce)
        trading = df.get("vol", pd.Series(dtype=float)).fillna(0) > 0

        return signal & trading
