"""KDJ 金叉策略。

逻辑：K 线上穿 D 线，且 J 值在低位（超卖区域）。
默认参数：oversold_j=20
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategy


class KDJGoldenStrategy(BaseStrategy):
    """KDJ 金叉策略：K 上穿 D 且 J 在低位。"""

    name = "kdj-golden"
    display_name = "KDJ金叉"
    category = "technical"
    description = "KDJ K线上穿D线，且J值处于超卖区域"
    default_params = {"oversold_j": 20}

    async def filter_batch(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        """检测 KDJ 金叉信号。"""
        oversold_j = self.params.get("oversold_j", 20)

        prev_k = df.get("kdj_k_prev", pd.Series(dtype=float)).fillna(50)
        prev_d = df.get("kdj_d_prev", pd.Series(dtype=float)).fillna(50)
        cur_k = df.get("kdj_k", pd.Series(dtype=float)).fillna(50)
        cur_d = df.get("kdj_d", pd.Series(dtype=float)).fillna(50)
        cur_j = df.get("kdj_j", pd.Series(dtype=float)).fillna(50)

        # K 上穿 D 且 J 在低位
        cross = (prev_k <= prev_d) & (cur_k > cur_d)
        oversold = cur_j < oversold_j
        trading = df.get("vol", pd.Series(dtype=float)).fillna(0) > 0

        return cross & oversold & trading
