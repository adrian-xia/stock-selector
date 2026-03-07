"""Trigger 策略：地量见底。

底部组信号，极端缩量 + 低换手 + 企稳确认。
返回 list[StrategySignal]，含置信度。
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategyV2, SignalGroup, StrategyRole, StrategySignal


class ExtremeShrinkBottomTriggerV2(BaseStrategyV2):
    """地量见底 Trigger：极端缩量 + 低换手率 + 非一字板。"""

    name = "extreme-shrink-bottom-trigger-v2"
    display_name = "地量见底"
    role = StrategyRole.TRIGGER
    signal_group = SignalGroup.BOTTOM
    description = "极端缩量+低换手率，阶段性底部信号"
    default_params = {
        "extreme_ratio": 0.3,
        "max_turnover": 1.0,
    }
    ai_rating = 6.33  # 三模型均分

    async def execute(
        self,
        df: pd.DataFrame,
        target_date: date,
    ) -> list[StrategySignal]:
        """执行地量见底检测。

        Returns:
            list[StrategySignal]，命中股票列表
        """
        extreme_ratio = self.params.get("extreme_ratio", 0.3)
        max_turnover = self.params.get("max_turnover", 1.0)

        high = df.get("high", pd.Series(dtype=float)).fillna(0)
        low = df.get("low", pd.Series(dtype=float)).fillna(0)
        pct_chg = df.get("pct_chg", pd.Series(dtype=float)).fillna(0)
        vol_ratio = df.get("vol_ratio", pd.Series(dtype=float)).fillna(0)
        turnover_rate = df.get("turnover_rate", pd.Series(dtype=float)).fillna(0)
        vol = df.get("vol", pd.Series(dtype=float)).fillna(0)

        extreme_shrink = vol_ratio < extreme_ratio
        low_turnover = turnover_rate < max_turnover
        not_doji = high > low
        not_limit_down = pct_chg > -9.5
        trading = vol > 0

        signal_mask = extreme_shrink & low_turnover & not_doji & not_limit_down & trading

        signals = []
        for ts_code in df.loc[signal_mask, "ts_code"]:
            signals.append(
                StrategySignal(
                    ts_code=ts_code,
                    confidence=1.0,
                )
            )

        return signals
