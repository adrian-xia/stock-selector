"""缩量回调策略。

逻辑：上升趋势中缩量回调至 MA20 支撑位。
默认参数：max_vol_ratio=0.6, ma_tolerance=0.02
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategy


class VolumeContractionPullbackStrategy(BaseStrategy):
    """缩量回调策略：上升趋势中缩量回踩 MA20 支撑。"""

    name = "volume-contraction-pullback"
    display_name = "缩量回调"
    category = "technical"
    description = "上升趋势中缩量回调至 MA20 支撑位"
    default_params = {"max_vol_ratio": 0.6, "ma_tolerance": 0.02}

    async def filter_batch(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        """检测缩量回调信号。"""
        max_vol_ratio = self.params.get("max_vol_ratio", 0.6)
        ma_tolerance = self.params.get("ma_tolerance", 0.02)

        close = df.get("close", pd.Series(dtype=float)).fillna(0)
        ma5 = df.get("ma5", pd.Series(dtype=float)).fillna(0)
        ma20 = df.get("ma20", pd.Series(dtype=float)).fillna(0)
        vol_ratio = df.get("vol_ratio", pd.Series(dtype=float)).fillna(0)

        # 上升趋势：MA5 > MA20
        uptrend = ma5 > ma20

        # 回调至 MA20 附近（容差范围内）
        near_ma20 = (close >= ma20 * (1 - ma_tolerance)) & (close <= ma20 * (1 + ma_tolerance))

        # 缩量
        low_volume = vol_ratio <= max_vol_ratio

        # MA20 有效
        valid = ma20 > 0

        # 排除停牌
        trading = df.get("vol", pd.Series(dtype=float)).fillna(0) > 0

        return uptrend & near_ma20 & low_volume & valid & trading
