"""Confirmer 策略：均线多头排列。

作为趋势方向确认，为趋势组信号 +0.3 加分。
返回加分系数 0.0-1.0（满足条件返回 1.0，否则 0.0）。
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategyV2, StrategyRole


class MALongArrangeConfirmerV2(BaseStrategyV2):
    """均线多头排列 Confirmer：趋势方向确认。"""

    name = "ma-long-arrange-confirmer-v2"
    display_name = "均线多头排列（确认）"
    role = StrategyRole.CONFIRMER
    signal_group = None
    description = "MA5 > MA10 > MA20 > MA60，为趋势组信号加分"
    default_params = {}
    ai_rating = 6.53  # 三模型均分（从独立策略降级为 confirmer）

    async def execute(
        self,
        df: pd.DataFrame,
        target_date: date,
    ) -> pd.Series:
        """执行确认检查。

        Returns:
            pd.Series[float]，索引为 ts_code，加分系数 0.0-1.0
            满足多头排列返回 1.0，否则 0.0
        """
        ma5 = df.get("ma5", pd.Series(dtype=float)).fillna(0)
        ma10 = df.get("ma10", pd.Series(dtype=float)).fillna(0)
        ma20 = df.get("ma20", pd.Series(dtype=float)).fillna(0)
        ma60 = df.get("ma60", pd.Series(dtype=float)).fillna(0)

        # 多头排列：MA5 > MA10 > MA20 > MA60，且 MA60 > 0（有效值）
        signal = (ma5 > ma10) & (ma10 > ma20) & (ma20 > ma60) & (ma60 > 0)
        trading = df.get("vol", pd.Series(dtype=float)).fillna(0) > 0

        # 转换为 float：True -> 1.0, False -> 0.0
        result = (signal & trading).astype(float)

        # 确保索引是 ts_code
        if "ts_code" in df.columns:
            result.index = df["ts_code"].values

        return result
