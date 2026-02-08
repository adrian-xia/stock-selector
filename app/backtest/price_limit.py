"""涨跌停检查器。

根据 A 股不同板块的涨跌停规则，判断股票是否处于涨停或跌停状态。
- 主板（60xxxx, 00xxxx）：±10%
- 创业板/科创板（30xxxx, 68xxxx）：±20%
- ST 股票：±5%
"""

import logging

logger = logging.getLogger(__name__)


def get_limit_pct(ts_code: str, name: str = "") -> float:
    """根据股票代码和名称返回涨跌停幅度。

    Args:
        ts_code: 股票代码，如 "600519.SH"
        name: 股票名称，用于判断 ST

    Returns:
        涨跌停幅度（小数），如 0.10 表示 10%
    """
    # ST 股票优先判断（±5%）
    if name and "ST" in name.upper():
        return 0.05

    # 提取纯数字代码
    code = ts_code.split(".")[0] if "." in ts_code else ts_code

    # 创业板（300xxx）和科创板（688xxx）：±20%
    if code.startswith("30") or code.startswith("68"):
        return 0.20

    # 主板（600xxx, 601xxx, 603xxx, 000xxx, 001xxx, 002xxx）：±10%
    return 0.10


def is_limit_up(
    close: float,
    pre_close: float,
    limit_pct: float,
) -> bool:
    """判断是否涨停。

    Args:
        close: 当日收盘价
        pre_close: 前日收盘价
        limit_pct: 涨跌停幅度（小数）

    Returns:
        True 表示涨停
    """
    if pre_close <= 0:
        return False
    limit_price = round(pre_close * (1 + limit_pct), 2)
    return close >= limit_price - 0.01


def is_limit_down(
    close: float,
    pre_close: float,
    limit_pct: float,
) -> bool:
    """判断是否跌停。

    Args:
        close: 当日收盘价
        pre_close: 前日收盘价
        limit_pct: 涨跌停幅度（小数）

    Returns:
        True 表示跌停
    """
    if pre_close <= 0:
        return False
    limit_price = round(pre_close * (1 - limit_pct), 2)
    return close <= limit_price + 0.01
