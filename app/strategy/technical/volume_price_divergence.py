"""量价背离策略。

逻辑：价格创近期新低但成交量萎缩，看涨背离。
默认参数：lookback=20
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategy


class VolumePriceDivergenceStrategy(BaseStrategy):
    """量价背离策略：价格新低但量能萎缩，看涨信号。"""

    name = "volume-price-divergence"
    display_name = "量价背离"
    category = "technical"
    description = "价格接近近期低点但成交量显著萎缩"
    default_params = {"lookback": 20}

    async def filter_batch(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        """检测量价背离信号。"""
        close = df.get("close", pd.Series(dtype=float)).fillna(0)
        vol = df.get("vol", pd.Series(dtype=float)).fillna(0)
        donchian_lower = df.get("donchian_lower", pd.Series(dtype=float)).fillna(0)
        vol_ratio = df.get("vol_ratio", pd.Series(dtype=float)).fillna(0)

        # 价格接近近期低点（在唐奇安下轨 2% 范围内）
        near_low = (close <= donchian_lower * 1.02) & (donchian_lower > 0)

        # 成交量萎缩（量比 < 0.7）
        volume_shrink = vol_ratio < 0.7

        # 排除停牌
        trading = vol > 0

        return near_low & volume_shrink & trading
