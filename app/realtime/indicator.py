"""盘中增量指标计算与信号检测。"""

import logging
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Signal:
    """策略信号。"""
    ts_code: str
    signal_type: str  # ma_golden_cross / ma_death_cross / rsi_oversold / rsi_overbought
    message: str


def compute_ma(prices: list[float], period: int) -> float | None:
    """计算移动平均线。"""
    if len(prices) < period:
        return None
    return float(np.mean(prices[-period:]))


def compute_rsi(prices: list[float], period: int = 14) -> float | None:
    """计算 RSI 指标。"""
    if len(prices) < period + 1:
        return None
    deltas = np.diff(prices[-(period + 1):])
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = float(np.mean(gains))
    avg_loss = float(np.mean(losses))
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100 - (100 / (1 + rs)))


def compute_macd(prices: list[float]) -> tuple[float, float, float] | None:
    """计算 MACD（DIF, DEA, MACD柱）。"""
    if len(prices) < 26:
        return None
    arr = np.array(prices, dtype=float)
    ema12 = _ema(arr, 12)
    ema26 = _ema(arr, 26)
    dif = ema12 - ema26
    # DEA = DIF 的 9 日 EMA（简化：取最近 9 个 DIF 的均值）
    dea = float(np.mean(dif[-9:])) if len(dif) >= 9 else float(dif[-1])
    macd_bar = 2 * (float(dif[-1]) - dea)
    return float(dif[-1]), dea, macd_bar


def _ema(data: np.ndarray, period: int) -> np.ndarray:
    """指数移动平均。"""
    alpha = 2 / (period + 1)
    result = np.zeros_like(data)
    result[0] = data[0]
    for i in range(1, len(data)):
        result[i] = alpha * data[i] + (1 - alpha) * result[i - 1]
    return result


def detect_signals(ts_code: str, prices: list[float]) -> list[Signal]:
    """检测策略信号：MA 金叉/死叉、RSI 超买/超卖。"""
    signals: list[Signal] = []

    if len(prices) < 20:
        return signals

    ma5 = compute_ma(prices, 5)
    ma10 = compute_ma(prices, 10)
    # 前一根的 MA
    ma5_prev = compute_ma(prices[:-1], 5)
    ma10_prev = compute_ma(prices[:-1], 10)

    if ma5 and ma10 and ma5_prev and ma10_prev:
        if ma5_prev <= ma10_prev and ma5 > ma10:
            signals.append(Signal(ts_code, "ma_golden_cross", f"{ts_code} MA5 上穿 MA10（金叉）"))
        elif ma5_prev >= ma10_prev and ma5 < ma10:
            signals.append(Signal(ts_code, "ma_death_cross", f"{ts_code} MA5 下穿 MA10（死叉）"))

    rsi = compute_rsi(prices)
    if rsi is not None:
        if rsi <= 30:
            signals.append(Signal(ts_code, "rsi_oversold", f"{ts_code} RSI={rsi:.1f} 超卖"))
        elif rsi >= 70:
            signals.append(Signal(ts_code, "rsi_overbought", f"{ts_code} RSI={rsi:.1f} 超买"))

    return signals
