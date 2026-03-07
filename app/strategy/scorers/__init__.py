"""V2 Scorer 策略：质量评分。

Scorer 输出连续分数（0-100），用于 Layer 1 质量底池评分。
"""

from app.strategy.scorers.quality_score_v2 import QualityScoreStrategyV2

__all__ = [
    "QualityScoreStrategyV2",
]
