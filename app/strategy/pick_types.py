"""通用选股结果类型。"""

from dataclasses import dataclass, field


@dataclass
class StockPick:
    """供 AI / 报告等通用流程使用的选股结果。"""

    ts_code: str
    name: str
    close: float
    pct_chg: float
    matched_strategies: list[str] = field(default_factory=list)
    match_count: int = 0
    weighted_score: float = 0.0
    ai_score: int | None = None
    ai_signal: str | None = None
    ai_summary: str | None = None
