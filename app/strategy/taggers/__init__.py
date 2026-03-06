"""V2 Tagger 策略：风格标签。

Tagger 输出 dict[str, pd.Series[float]]，风格强度 0.0-1.0。
用于 Layer 1 为股票打风格标签（成长/价值/红利等）。
"""

from app.strategy.adapters.tagger_adapter import TaggerAdapter
from app.strategy.fundamental.high_dividend import HighDividendStrategy
from app.strategy.fundamental.low_pe_high_roe import LowPEHighROEStrategy

# 使用 TaggerAdapter 包装 V1 基本面策略为 V2 Tagger
LowPEHighROETaggerV2 = TaggerAdapter(
    LowPEHighROEStrategy(),
    style_key="growth",  # 成长风格
    ai_rating=7.13,  # 三模型均分
)

HighDividendTaggerV2 = TaggerAdapter(
    HighDividendStrategy(),
    style_key="dividend",  # 红利风格
    ai_rating=6.47,  # 三模型均分
)

__all__ = [
    "LowPEHighROETaggerV2",
    "HighDividendTaggerV2",
]
