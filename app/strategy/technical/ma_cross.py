"""均线金叉策略。

逻辑：短期均线上穿长期均线，且成交量放大。
默认参数：fast=5, slow=10, vol_ratio=1.5
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategy


class MACrossStrategy(BaseStrategy):
    """均线金叉策略：MA(fast) 上穿 MA(slow) + 放量确认。"""

    name = "ma-cross"
    display_name = "均线金叉"
    category = "technical"
    description = "短期均线上穿长期均线，且成交量放大"
    default_params = {"fast": 5, "slow": 10, "vol_ratio": 1.5}

    async def filter_batch(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        """检测均线金叉信号。"""
        fast = self.params.get("fast", 5)
        slow = self.params.get("slow", 10)
        vol_ratio = self.params.get("vol_ratio", 1.5)

        fast_col = f"ma{fast}"
        slow_col = f"ma{slow}"
        prev_fast = f"ma{fast}_prev"
        prev_slow = f"ma{slow}_prev"

        # 金叉：昨日短期 <= 长期，今日短期 > 长期
        cross = (
            (df.get(prev_fast, pd.Series(dtype=float)).fillna(0) <= df.get(prev_slow, pd.Series(dtype=float)).fillna(0))
            & (df.get(fast_col, pd.Series(dtype=float)).fillna(0) > df.get(slow_col, pd.Series(dtype=float)).fillna(0))
        )

        # 放量确认
        volume_ok = df.get("vol_ratio", pd.Series(dtype=float)).fillna(0) >= vol_ratio

        # 排除停牌
        trading = df.get("vol", pd.Series(dtype=float)).fillna(0) > 0

        return cross & volume_ok & trading
