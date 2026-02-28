"""V4 回测数据模型。"""

from dataclasses import dataclass, field
from datetime import date


@dataclass
class BacktestSignal:
    ts_code: str
    signal_date: date
    t0_date: date
    entry_price: float
    market_state: str = "neutral"
    ret_1d: float | None = None
    ret_3d: float | None = None
    ret_5d: float | None = None
    ret_10d: float | None = None


@dataclass
class BacktestMetrics:
    total_signals: int = 0
    signals_per_month: float = 0.0
    win_rate_1d: float = 0.0
    win_rate_3d: float = 0.0
    win_rate_5d: float = 0.0
    win_rate_10d: float = 0.0
    avg_ret_5d: float = 0.0
    profit_loss_ratio: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0


@dataclass
class GridSearchResult:
    params: dict = field(default_factory=dict)
    metrics: BacktestMetrics = field(default_factory=BacktestMetrics)
    score: float = 0.0
