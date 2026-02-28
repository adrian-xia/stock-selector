"""V4 回测评估指标计算。"""

import statistics
from app.v4backtest.models import BacktestSignal, BacktestMetrics


def _win_rate(signals: list[BacktestSignal], attr: str) -> float:
    vals = [getattr(s, attr) for s in signals if getattr(s, attr) is not None]
    return round(len([v for v in vals if v > 0]) / len(vals), 4) if vals else 0.0


def evaluate_signals(signals: list[BacktestSignal]) -> BacktestMetrics:
    if not signals:
        return BacktestMetrics()

    rets_5d = [s.ret_5d for s in signals if s.ret_5d is not None]
    rets_10d = [s.ret_10d for s in signals if s.ret_10d is not None]

    # 盈亏比
    wins = [r for r in rets_5d if r > 0]
    losses = [r for r in rets_5d if r < 0]
    avg_win = sum(wins) / len(wins) if wins else 0
    avg_loss = abs(sum(losses) / len(losses)) if losses else 1
    plr = round(avg_win / avg_loss, 2) if avg_loss > 0 else 0

    # 最大回撤
    cum, peak, max_dd = 0.0, 0.0, 0.0
    for r in rets_10d:
        cum += r
        peak = max(peak, cum)
        max_dd = max(max_dd, peak - cum)

    # 夏普比率
    sharpe = 0.0
    if len(rets_5d) > 1:
        mean_r = statistics.mean(rets_5d)
        std_r = statistics.stdev(rets_5d)
        if std_r > 0:
            sharpe = round((mean_r - 0.03 / 50) / std_r * (50 ** 0.5), 2)

    # 信号频率
    spm = 0.0
    if len(signals) >= 2:
        days = (signals[-1].signal_date - signals[0].signal_date).days
        spm = round(len(signals) / max(days / 30, 1), 1)

    return BacktestMetrics(
        total_signals=len(signals),
        signals_per_month=spm,
        win_rate_1d=_win_rate(signals, "ret_1d"),
        win_rate_3d=_win_rate(signals, "ret_3d"),
        win_rate_5d=_win_rate(signals, "ret_5d"),
        win_rate_10d=_win_rate(signals, "ret_10d"),
        avg_ret_5d=round(statistics.mean(rets_5d), 4) if rets_5d else 0,
        profit_loss_ratio=plr,
        max_drawdown=round(max_dd, 4),
        sharpe_ratio=sharpe,
    )
