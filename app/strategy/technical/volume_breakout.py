"""放量突破策略。

逻辑：价格创 N 日新高，且量比超过阈值。
默认参数：high_period=20, min_vol_ratio=2.0
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategy


class VolumeBreakoutStrategy(BaseStrategy):
    """放量突破策略：创新高 + 放量。"""

    name = "volume-breakout"
    display_name = "放量突破"
    category = "technical"
    description = "价格创近期新高且成交量显著放大"
    default_params = {"high_period": 20, "min_vol_ratio": 2.0}

    async def filter_batch(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        """检测放量突破信号。

        注意：此策略需要 Pipeline 在构建市场快照时提供 high_20 列
        （过去 20 日最高价）。如果该列不存在，使用 close 与 ma20 的
        简化判断：close > ma20 * 1.05（价格高于 20 日均线 5%）。
        """
        min_vol_ratio = self.params.get("min_vol_ratio", 2.0)

        cur_close = df.get("close", pd.Series(dtype=float)).fillna(0)
        vol_ratio = df.get("vol_ratio", pd.Series(dtype=float)).fillna(0)

        # 优先使用 high_20 列（Pipeline 预计算），否则用 ma20 近似
        if "high_20" in df.columns:
            price_breakout = cur_close >= df["high_20"].fillna(float("inf"))
        else:
            ma20 = df.get("ma20", pd.Series(dtype=float)).fillna(0)
            # 简化判断：收盘价高于 20 日均线 5%
            price_breakout = (ma20 > 0) & (cur_close > ma20 * 1.05)

        volume_ok = vol_ratio >= min_vol_ratio
        trading = df.get("vol", pd.Series(dtype=float)).fillna(0) > 0

        return price_breakout & volume_ok & trading
