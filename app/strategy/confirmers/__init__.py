"""V2 Confirmer 策略：辅助确认信号。

Confirmer 不独立触发，为已触发信号提供加分/减分。
返回加分系数 0.0-1.0，在 Layer 3 融合排序时叠加。
"""

from app.strategy.confirmers.bias_extreme_v2 import BIASExtremeConfirmerV2
from app.strategy.confirmers.ma_long_arrange_v2 import MALongArrangeConfirmerV2
from app.strategy.confirmers.macd_divergence_v2 import MACDDivergenceConfirmerV2
from app.strategy.confirmers.rsi_oversold_v2 import RSIOversoldConfirmerV2
from app.strategy.confirmers.shrink_volume_rise_v2 import ShrinkVolumeRiseConfirmerV2

__all__ = [
    "MALongArrangeConfirmerV2",
    "RSIOversoldConfirmerV2",
    "BIASExtremeConfirmerV2",
    "MACDDivergenceConfirmerV2",
    "ShrinkVolumeRiseConfirmerV2",
]
