"""V2 Trigger 策略：信号触发。

Trigger 输出 list[StrategySignal]，含置信度。
分为三组：aggressive（进攻）、trend（趋势）、bottom（底部）。
"""

from app.strategy.triggers.atr_breakout_v2 import ATRBreakoutTriggerV2
from app.strategy.triggers.dragon_turnaround_v2 import DragonTurnaroundTriggerV2
from app.strategy.triggers.extreme_shrink_bottom_v2 import (
    ExtremeShrinkBottomTriggerV2,
)
from app.strategy.triggers.first_negative_reversal_v2 import (
    FirstNegativeReversalTriggerV2,
)
from app.strategy.triggers.peak_pullback_stabilization_v2 import (
    PeakPullbackStabilizationTriggerV2,
)
from app.strategy.triggers.pullback_half_rule_v2 import PullbackHalfRuleTriggerV2
from app.strategy.triggers.volume_breakout_v2 import VolumeBreakoutTriggerV2
from app.strategy.triggers.volume_contraction_pullback_v2 import (
    VolumeContractionPullbackTriggerV2,
)
from app.strategy.triggers.volume_price_stable_v2 import VolumePriceStableTriggerV2
from app.strategy.triggers.volume_surge_continuation_v2 import (
    VolumeSurgeContinuationTriggerV2,
)

__all__ = [
    # 进攻组（4 个）
    "DragonTurnaroundTriggerV2",
    "FirstNegativeReversalTriggerV2",
    "VolumeBreakoutTriggerV2",
    "VolumeSurgeContinuationTriggerV2",
    # 趋势组（4 个）
    "VolumeContractionPullbackTriggerV2",
    "PeakPullbackStabilizationTriggerV2",
    "PullbackHalfRuleTriggerV2",
    "ATRBreakoutTriggerV2",
    # 底部组（2 个）
    "ExtremeShrinkBottomTriggerV2",
    "VolumePriceStableTriggerV2",
]
