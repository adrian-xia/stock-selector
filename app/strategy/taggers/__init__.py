"""V2 Tagger 策略：风格标签。

Tagger 输出 dict[str, pd.Series[float]]，风格强度 0.0-1.0。
用于 Layer 1 为股票打风格标签（成长/价值/红利等）。
"""

from app.strategy.adapters.tagger_adapter import TaggerAdapter
from app.strategy.fundamental.high_dividend import HighDividendStrategy
from app.strategy.fundamental.low_pe_high_roe import LowPEHighROEStrategy


def _make_low_pe_high_roe_tagger(params=None):
    """工厂函数：创建低估值高成长 Tagger 实例。"""
    return TaggerAdapter(
        LowPEHighROEStrategy(params),
        style_key="growth",
        ai_rating=7.13,
    )


def _make_high_dividend_tagger(params=None):
    """工厂函数：创建高股息 Tagger 实例。"""
    return TaggerAdapter(
        HighDividendStrategy(params),
        style_key="dividend",
        ai_rating=6.47,
    )


# 导出类（用于注册）
LowPEHighROETaggerV2 = type(
    "LowPEHighROETaggerV2",
    (),
    {"__call__": staticmethod(_make_low_pe_high_roe_tagger)},
)

HighDividendTaggerV2 = type(
    "HighDividendTaggerV2",
    (),
    {"__call__": staticmethod(_make_high_dividend_tagger)},
)

__all__ = [
    "LowPEHighROETaggerV2",
    "HighDividendTaggerV2",
]
