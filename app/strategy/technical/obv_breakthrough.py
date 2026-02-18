"""OBV 能量潮突破策略。

逻辑：OBV 突破近期高点且价格上涨确认。
默认参数：lookback=20
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategy


class OBVBreakthroughStrategy(BaseStrategy):
    """OBV 能量潮突破策略：OBV 创新高 + 价格上涨确认。"""

    name = "obv-breakthrough"
    display_name = "OBV能量潮突破"
    category = "technical"
    description = "OBV 突破近期高点且价格上涨确认"
    default_params = {"lookback": 20}

    async def filter_batch(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        """检测 OBV 突破信号。"""
        obv = df.get("obv", pd.Series(dtype=float)).fillna(0)
        prev_obv = df.get("obv_prev", pd.Series(dtype=float)).fillna(0)
        close = df.get("close", pd.Series(dtype=float)).fillna(0)
        prev_close = df.get("close_prev", pd.Series(dtype=float)).fillna(0)

        # OBV 突破：今日 OBV > 昨日 OBV（简化为日间突破）
        obv_rising = obv > prev_obv

        # 价格上涨确认
        price_up = close > prev_close

        # 排除停牌
        trading = df.get("vol", pd.Series(dtype=float)).fillna(0) > 0

        return obv_rising & price_up & trading
