"""MACD 底背离策略。

逻辑：在 lookback 周期内，价格创新低但 MACD DIF 不创新低，
表明下跌动能减弱，可能反转。
默认参数：lookback=20
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategy


class MACDDivergenceStrategy(BaseStrategy):
    """MACD 底背离策略：价格新低但 DIF 不创新低。"""

    name = "macd-divergence"
    display_name = "MACD底背离"
    category = "technical"
    description = "价格创近期新低但MACD DIF未创新低，下跌动能减弱"
    default_params = {"lookback": 20}

    async def filter_batch(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        """检测 MACD 底背离信号。

        简化实现：比较当前值与 lookback 周期内的最低值。
        需要 Pipeline 提供 close_min_{lookback} 和 dif_min_{lookback} 列，
        如果不存在则使用 close_prev 和 macd_dif_prev 做简化判断。
        """
        lookback = self.params.get("lookback", 20)

        cur_close = df.get("close", pd.Series(dtype=float)).fillna(0)
        cur_dif = df.get("macd_dif", pd.Series(dtype=float)).fillna(0)

        # 优先使用 Pipeline 预计算的周期最低值列
        close_min_col = f"close_min_{lookback}"
        dif_min_col = f"dif_min_{lookback}"

        if close_min_col in df.columns and dif_min_col in df.columns:
            prev_close_min = df[close_min_col].fillna(float("inf"))
            prev_dif_min = df[dif_min_col].fillna(0)
        else:
            # 简化判断：使用前日数据近似
            prev_close_min = df.get(
                "close_prev", pd.Series(dtype=float)
            ).fillna(float("inf"))
            prev_dif_min = df.get(
                "macd_dif_prev", pd.Series(dtype=float)
            ).fillna(0)

        # 底背离：当前价格 <= 前期低点，但 DIF > 前期 DIF 低点
        price_new_low = cur_close <= prev_close_min
        dif_higher = cur_dif > prev_dif_min

        signal = price_new_low & dif_higher
        trading = df.get("vol", pd.Series(dtype=float)).fillna(0) > 0

        return signal & trading
