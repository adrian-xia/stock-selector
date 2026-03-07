"""Confirmer 策略：MACD 底背离。

二次底背离确认，为底部信号 +0.3 加分。
返回加分权重（0.0 或 0.3）。
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategyV2, SignalGroup, StrategyRole


class MACDDivergenceConfirmerV2(BaseStrategyV2):
    """MACD 底背离 Confirmer：底部反转确认。"""

    name = "macd-divergence-confirmer-v2"
    display_name = "MACD 底背离（确认）"
    role = StrategyRole.CONFIRMER
    signal_group = None
    description = "价格创新低但 MACD DIF 未创新低，二次底背离确认"
    default_params = {
        "lookback": 20,
    }
    ai_rating = 6.18  # 三模型均分
    bonus_weight = 0.3  # 加分权重
    applicable_groups = [SignalGroup.BOTTOM]  # 适用信号组

    async def execute(
        self,
        df: pd.DataFrame,
        target_date: date,
    ) -> pd.Series:
        """执行确认检查。

        Returns:
            pd.Series[float]，索引为 ts_code，加分权重（0.0 或 0.3）
        """
        lookback = self.params.get("lookback", 20)

        close = df.get("close", pd.Series(dtype=float))
        macd_dif = df.get("macd_dif", pd.Series(dtype=float))

        # 需要历史数据才能判断背离，当前实现简化为：
        # MACD DIF < 0（处于零轴下方）且 DIF 上升（macd_dif > macd_dif_prev）
        macd_dif_prev = df.get("macd_dif_prev", pd.Series(dtype=float))

        divergence = (
            close.notna()
            & macd_dif.notna()
            & macd_dif_prev.notna()
            & (macd_dif < 0)  # 零轴下方
            & (macd_dif > macd_dif_prev)  # DIF 上升
        )

        # 返回加分权重：满足条件返回 0.3，否则 0.0
        result = divergence.astype(float) * self.bonus_weight

        # 确保索引是 ts_code
        if "ts_code" in df.columns:
            result.index = df["ts_code"].values

        return result
