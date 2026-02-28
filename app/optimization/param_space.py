"""参数空间工具函数：生成参数组合和计算组合数。"""

import itertools
import math


def _normalize_spec(spec) -> dict:
    """将 tuple 格式 (min, max, step) 转换为 dict 格式。"""
    if isinstance(spec, (tuple, list)):
        min_val, max_val, step = spec[0], spec[1], spec[2]
        param_type = "int" if all(isinstance(v, int) for v in (min_val, max_val, step)) else "float"
        return {"type": param_type, "min": min_val, "max": max_val, "step": step}
    return spec


def _generate_range(spec) -> list:
    """根据参数规格生成取值列表。

    Args:
        spec: {"type": "int"|"float", "min": N, "max": N, "step": N}
              或 (min, max, step) tuple

    Returns:
        参数取值列表
    """
    spec = _normalize_spec(spec)
    param_type = spec["type"]
    min_val = spec["min"]
    max_val = spec["max"]
    step = spec["step"]

    if step <= 0:
        raise ValueError(f"step 必须大于 0，当前值: {step}")

    values = []
    current = min_val
    # 使用 round 避免浮点精度问题
    while current <= max_val + 1e-9:
        if param_type == "int":
            values.append(int(round(current)))
        else:
            values.append(round(current, 6))
        current += step

    return values


def generate_combinations(param_space: dict) -> list[dict]:
    """生成参数空间的所有组合。

    Args:
        param_space: 参数空间定义
            {"param_name": {"type": "int"|"float", "min": N, "max": N, "step": N}}

    Returns:
        所有参数组合的列表，每个元素为 {param_name: value} 字典
    """
    if not param_space:
        return [{}]

    param_names = list(param_space.keys())
    param_ranges = [_generate_range(param_space[name]) for name in param_names]

    combinations = []
    for values in itertools.product(*param_ranges):
        combo = dict(zip(param_names, values))
        combinations.append(combo)

    return combinations


def count_combinations(param_space: dict) -> int:
    """计算参数空间的总组合数（不实际生成）。

    Args:
        param_space: 参数空间定义

    Returns:
        总组合数
    """
    if not param_space:
        return 1

    total = 1
    for spec in param_space.values():
        spec = _normalize_spec(spec)
        min_val = spec["min"]
        max_val = spec["max"]
        step = spec["step"]
        count = math.floor((max_val - min_val) / step) + 1
        total *= max(count, 1)

    return total
