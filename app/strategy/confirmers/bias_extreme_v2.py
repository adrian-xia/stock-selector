"""Confirmer 策略：BIAS 极端乖离。

乖离率历史分位数 < 5%，为反弹信号 +0.2 加分。
返回加分权重（0.0 或 0.2）。
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategyV2, SignalGroup, StrategyRole


class BIASExtremeConfirmerV2(BaseStrategyV2):
    """BIAS 极端乖离 Confirmer：超跌反弹确认。"""

    name = "bias-extreme-confirmer-v2"
    display_name = "BIAS 极端乖离（确认）"
    role = StrategyRole.CONFIRMER
    signal_group = None
    description = "BIAS 乖离率达到极端超卖（<-6%），为反弹信号加分"
    default_params = {
        "oversold_bias": -6.0,
    }
    ai_rating = 5.80  # 三模型均分
    bonus_weight = 0.2  # 加分权重
    applicable_groups = [SignalGroup.BOTTOM_REVERSAL]  # 适用信号组

    async def execute(
        self,
        df: pd.DataFrame,
        target_date: date,
    ) -> pd.Series:
        """执行确认检查。

        Returns:
            pd.Series[float]，索引为 ts_code，加分权重（0.0 或 0.2）
        """
        oversold_bias = self.params.get("oversold_bias", -6.0)

        close = df.get("close", pd.Series(dtype=float))
        ma20 = df.get("ma20", pd.Series(dtype=float))

        # 计算 BIAS = (close - ma20) / ma20 * 100
        bias = ((close - ma20) / ma20 * 100).fillna(0)

        # 极端乖离：BIAS < oversold_bias（如 -6%）
        extreme = (bias < oversold_bias) & (ma20 > 0)

        # 返回加分权重：满足条件返回 0.2，否则 0.0
        result = extreme.astype(float) * self.bonus_weight

        # 确保索引是 ts_code
        if "ts_code" in df.columns:
            result.index = df["ts_code"].values

        return result
