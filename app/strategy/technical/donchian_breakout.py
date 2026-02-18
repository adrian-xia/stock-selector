"""唐奇安通道突破策略。

逻辑：价格突破 20 日唐奇安通道上轨。
默认参数：period=20
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategy


class DonchianBreakoutStrategy(BaseStrategy):
    """唐奇安通道突破策略：价格从通道内突破上轨。"""

    name = "donchian-breakout"
    display_name = "唐奇安通道突破"
    category = "technical"
    description = "价格突破 20 日唐奇安通道上轨"
    default_params = {"period": 20}

    async def filter_batch(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        """检测唐奇安通道突破信号。"""
        close = df.get("close", pd.Series(dtype=float)).fillna(0)
        prev_close = df.get("close_prev", pd.Series(dtype=float)).fillna(0)
        donchian_upper = df.get("donchian_upper", pd.Series(dtype=float)).fillna(0)
        prev_donchian_upper = df.get("donchian_upper_prev", pd.Series(dtype=float)).fillna(0)

        # 突破：昨日收盘 <= 上轨，今日收盘 > 上轨
        breakout = (prev_close <= prev_donchian_upper) & (close > donchian_upper)

        # 上轨有效（非零）
        valid = donchian_upper > 0

        # 排除停牌
        trading = df.get("vol", pd.Series(dtype=float)).fillna(0) > 0

        return breakout & valid & trading
