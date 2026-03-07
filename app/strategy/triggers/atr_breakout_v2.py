"""Trigger 策略：ATR 波动率突破。

趋势组信号，自适应波动率突破，捕捉横盘后异动。
返回 list[StrategySignal]，含置信度。
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategyV2, SignalGroup, StrategyRole, StrategySignal


class ATRBreakoutTriggerV2(BaseStrategyV2):
    """ATR 波动率突破 Trigger：价格突破均线 + ATR 波动带。"""

    name = "atr-breakout-trigger-v2"
    display_name = "ATR波动率突破"
    role = StrategyRole.TRIGGER
    signal_group = SignalGroup.TREND
    description = "价格突破 MA20 + ATR14 波动带上轨"
    default_params = {
        "atr_multiplier": 1.5,
    }
    ai_rating = 6.67  # 三模型均分

    async def execute(
        self,
        df: pd.DataFrame,
        target_date: date,
    ) -> list[StrategySignal]:
        """执行 ATR 波动率突破检测。

        Returns:
            list[StrategySignal]，命中股票列表
        """
        multiplier = self.params.get("atr_multiplier", 1.5)

        close = df.get("close", pd.Series(dtype=float)).fillna(0)
        ma20 = df.get("ma20", pd.Series(dtype=float)).fillna(0)
        atr14 = df.get("atr14", pd.Series(dtype=float)).fillna(0)
        prev_close = df.get("close_prev", pd.Series(dtype=float)).fillna(0)
        prev_ma20 = df.get("ma20_prev", pd.Series(dtype=float)).fillna(0)
        prev_atr14 = df.get("atr14_prev", pd.Series(dtype=float)).fillna(0)

        # 突破：今日收盘 > MA20 + ATR * 倍数，且昨日未突破
        upper_band = ma20 + atr14 * multiplier
        prev_upper_band = prev_ma20 + prev_atr14 * multiplier
        breakout = (close > upper_band) & (prev_close <= prev_upper_band)

        # 指标有效
        valid = (ma20 > 0) & (atr14 > 0)

        # 排除停牌
        trading = df.get("vol", pd.Series(dtype=float)).fillna(0) > 0

        signal_mask = breakout & valid & trading

        signals = []
        for ts_code in df.loc[signal_mask, "ts_code"]:
            signals.append(
                StrategySignal(
                    ts_code=ts_code,
                    confidence=1.0,
                )
            )

        return signals
