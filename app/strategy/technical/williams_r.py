"""Williams %R 超卖反弹策略。

逻辑：Williams %R 从超卖区反弹。
默认参数：oversold=-80, bounce=-50
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategy


class WilliamsRStrategy(BaseStrategy):
    """Williams %R 超卖反弹策略：WR 从超卖区回升。"""

    name = "williams-r"
    display_name = "Williams %R超卖反弹"
    category = "technical"
    description = "Williams %R 从超卖区（<-80）反弹至 -50 以上"
    default_params = {"oversold": -80, "bounce": -50}

    async def filter_batch(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        """检测 Williams %R 超卖反弹信号。"""
        oversold = self.params.get("oversold", -80)
        bounce = self.params.get("bounce", -50)

        wr = df.get("wr", pd.Series(dtype=float)).fillna(0)
        prev_wr = df.get("wr_prev", pd.Series(dtype=float)).fillna(0)

        # 反弹：昨日 WR <= 超卖线，今日 WR > 反弹线
        signal = (prev_wr <= oversold) & (wr > bounce)

        # 排除停牌
        trading = df.get("vol", pd.Series(dtype=float)).fillna(0) > 0

        return signal & trading
