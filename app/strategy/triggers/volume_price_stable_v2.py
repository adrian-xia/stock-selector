"""Trigger 策略：量缩价稳。

底部组信号，抛压耗尽的底部企稳特征。
返回 list[StrategySignal]，含置信度。
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategyV2, SignalGroup, StrategyRole, StrategySignal


class VolumePriceStableTriggerV2(BaseStrategyV2):
    """量缩价稳 Trigger：缩量 + 价格企稳 + 经历调整。"""

    name = "volume-price-stable-trigger-v2"
    display_name = "量缩价稳"
    role = StrategyRole.TRIGGER
    signal_group = SignalGroup.BOTTOM
    description = "量缩价稳，抛压耗尽的底部企稳信号"
    default_params = {
        "max_vol_ratio": 0.5,
        "max_pct_chg": 2.0,
        "ma_position": 1.02,
    }
    ai_rating = 6.07  # 三模型均分

    async def execute(
        self,
        df: pd.DataFrame,
        target_date: date,
    ) -> list[StrategySignal]:
        """执行量缩价稳检测。

        Returns:
            list[StrategySignal]，命中股票列表
        """
        max_vol_ratio = self.params.get("max_vol_ratio", 0.5)
        max_pct_chg = self.params.get("max_pct_chg", 2.0)
        ma_position = self.params.get("ma_position", 1.02)

        close = df.get("close", pd.Series(dtype=float)).fillna(0)
        ma20 = df.get("ma20", pd.Series(dtype=float)).fillna(0)
        pct_chg = df.get("pct_chg", pd.Series(dtype=float)).fillna(0)
        vol_ratio = df.get("vol_ratio", pd.Series(dtype=float)).fillna(0)
        vol = df.get("vol", pd.Series(dtype=float)).fillna(0)

        shrink = vol_ratio < max_vol_ratio
        stable = pct_chg.abs() < max_pct_chg
        adjusted = (ma20 > 0) & (close <= ma20 * ma_position)
        not_limit_down = pct_chg > -9.5
        trading = vol > 0

        signal_mask = shrink & stable & adjusted & not_limit_down & trading

        signals = []
        for ts_code in df.loc[signal_mask, "ts_code"]:
            signals.append(
                StrategySignal(
                    ts_code=ts_code,
                    confidence=1.0,
                )
            )

        return signals
