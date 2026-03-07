"""V1 → V2 策略适配器。

Guard/Tagger 策略可以通过适配器复用 V1 filter_batch 方法。
Scorer/Confirmer 必须全新实现，因为 V1 只返回 bool，无法逆推连续分数。
"""

from app.strategy.adapters.guard_adapter import GuardAdapter
from app.strategy.adapters.tagger_adapter import TaggerAdapter

__all__ = ["GuardAdapter", "TaggerAdapter"]
