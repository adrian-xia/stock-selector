"""CCI 超买超卖策略。

逻辑：CCI 从超卖区反弹。
默认参数：oversold=-100, bounce=-80
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategy


class CCIOverboughtOversoldStrategy(BaseStrategy):
    """CCI 超买超卖策略：CCI 从超卖区回升。"""

    name = "cci-oversold"
    display_name = "CCI超买超卖"
    category = "technical"
    description = "CCI 从超卖区（<-100）反弹至 -80 以上"
    default_params = {"oversold": -100, "bounce": -80}

    async def filter_batch(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        """检测 CCI 超卖反弹信号。"""
        oversold = self.params.get("oversold", -100)
        bounce = self.params.get("bounce", -80)

        cci = df.get("cci", pd.Series(dtype=float)).fillna(0)
        prev_cci = df.get("cci_prev", pd.Series(dtype=float)).fillna(0)

        # 反弹：昨日 CCI <= 超卖线，今日 CCI > 反弹线
        signal = (prev_cci <= oversold) & (cci > bounce)

        # 排除停牌
        trading = df.get("vol", pd.Series(dtype=float)).fillna(0) > 0

        return signal & trading
