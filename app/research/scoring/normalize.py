"""归一化工具：percentile_rank 与 min-max 缩放。

设计文档 §6.3 要求全市场 percentile_rank 归一化，
小样本（<30）时禁止重新 percentile，退化为 min-max。
"""

import logging
from typing import Sequence

logger = logging.getLogger(__name__)


def percentile_rank(values: Sequence[float], min_samples: int = 30) -> list[float]:
    """计算 percentile rank 归一化（0~100）。

    对每个值计算其在全序列中的百分位排名。
    当样本数 < min_samples 时退化为 min-max 缩放。

    Args:
        values: 原始数值序列
        min_samples: 最小样本数，低于此值退化为 min-max

    Returns:
        归一化后的值列表（0~100）
    """
    n = len(values)
    if n == 0:
        return []
    if n == 1:
        return [50.0]

    # 小样本退化为 min-max
    if n < min_samples:
        return min_max_scale(values)

    # 排名法 percentile
    sorted_vals = sorted(values)
    result: list[float] = []
    for v in values:
        # 计算小于等于 v 的比例
        rank = sum(1 for sv in sorted_vals if sv <= v)
        pct = (rank / n) * 100
        result.append(round(pct, 2))

    return result


def min_max_scale(values: Sequence[float], target_min: float = 0.0, target_max: float = 100.0) -> list[float]:
    """Min-Max 缩放（降级方案）。

    Args:
        values: 原始数值序列
        target_min: 目标最小值
        target_max: 目标最大值

    Returns:
        缩放后的值列表
    """
    if not values:
        return []

    v_min = min(values)
    v_max = max(values)
    v_range = v_max - v_min

    if v_range == 0:
        # 所有值相同，返回中间值
        mid = (target_min + target_max) / 2
        return [mid] * len(values)

    scale = target_max - target_min
    return [
        round(target_min + ((v - v_min) / v_range) * scale, 2)
        for v in values
    ]


def normalize_scores(
    scores: dict[str, float],
    min_samples: int = 30,
) -> dict[str, float]:
    """对字典形式的分数进行 percentile rank 归一化。

    Args:
        scores: {key: raw_score} 字典
        min_samples: 最小样本数

    Returns:
        {key: normalized_score} 字典
    """
    if not scores:
        return {}

    keys = list(scores.keys())
    values = [scores[k] for k in keys]
    normalized = percentile_rank(values, min_samples)

    return dict(zip(keys, normalized))
