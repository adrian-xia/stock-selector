"""AI 分析 Prompt 模板。

从 YAML 文件加载模板，构建发送给 Gemini 的综合分析提示词。
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from app.strategy.pipeline import StockPick

logger = logging.getLogger(__name__)

# YAML 模板目录
_PROMPTS_DIR = Path(__file__).parent / "prompts"

# 模板缓存
_template_cache: dict[str, dict[str, Any]] = {}


def _load_template(name: str = "stock_analysis_v1") -> dict[str, Any]:
    """加载并缓存 YAML Prompt 模板。

    Args:
        name: 模板文件名（不含 .yaml 后缀）

    Returns:
        模板字典，包含 version, system_prompt, user_prompt_template, output_schema
    """
    if name in _template_cache:
        return _template_cache[name]

    path = _PROMPTS_DIR / f"{name}.yaml"
    if not path.exists():
        logger.warning("Prompt 模板 %s 不存在，使用内置默认模板", path)
        return _get_fallback_template()

    with open(path, encoding="utf-8") as f:
        template = yaml.safe_load(f)

    _template_cache[name] = template
    return template


def _get_fallback_template() -> dict[str, Any]:
    """内置默认模板（YAML 文件缺失时的降级方案）。"""
    return {
        "version": "v1-fallback",
        "system_prompt": "你是一名资深 A 股投资分析师。",
        "user_prompt_template": (
            "请对以下 {stock_count} 只候选股票进行综合分析。\n\n"
            "分析日期：{target_date}\n\n候选股票数据：\n{stocks_text}\n\n"
            "请严格按以下 JSON 格式返回：\n{output_schema}\n\n"
            "注意：必须对每只股票都给出分析，analysis 数组长度必须等于 {stock_count}。"
        ),
        "output_schema": (
            '{{\n  "analysis": [\n    {{\n'
            '      "ts_code": "股票代码",\n'
            '      "score": 0到100的整数评分,\n'
            '      "signal": "STRONG_BUY 或 BUY 或 HOLD 或 SELL 或 STRONG_SELL",\n'
            '      "reasoning": "简要分析理由（中文，50字以内）"\n'
            "    }}\n  ]\n}}"
        ),
    }


def get_prompt_version(template_name: str = "stock_analysis_v1") -> str:
    """获取当前 Prompt 模板版本号。"""
    template = _load_template(template_name)
    return template.get("version", "unknown")


def build_analysis_prompt(
    picks: list[StockPick],
    market_data: dict[str, dict],
    target_date: date,
    template_name: str = "stock_analysis_v1",
) -> str:
    """构建批量股票综合分析 Prompt。

    Args:
        picks: Layer 4 候选股票列表
        market_data: ts_code -> 指标数据字典
        target_date: 分析日期
        template_name: YAML 模板名称

    Returns:
        完整的分析提示词字符串
    """
    template = _load_template(template_name)

    # 构建每只股票的数据描述
    stock_sections: list[str] = []
    for pick in picks:
        data = market_data.get(pick.ts_code)
        if data:
            section = _format_stock_data(pick, data)
        else:
            section = (
                f"- {pick.ts_code} {pick.name}：数据缺失，"
                f"收盘价 {pick.close:.2f}，涨跌幅 {pick.pct_chg:.2f}%，"
                f"命中策略：{', '.join(pick.matched_strategies)}"
            )
        stock_sections.append(section)

    stocks_text = "\n".join(stock_sections)
    output_schema = template.get("output_schema", "")

    # 组装 system_prompt + user_prompt
    system_prompt = template.get("system_prompt", "").strip()
    user_prompt = template["user_prompt_template"].format(
        stock_count=len(picks),
        target_date=target_date.isoformat(),
        stocks_text=stocks_text,
        output_schema=output_schema,
    )

    if system_prompt:
        return f"{system_prompt}\n\n{user_prompt}"
    return user_prompt


def _format_stock_data(pick: StockPick, data: dict) -> str:
    """格式化单只股票的数据描述。"""
    parts = [f"- {pick.ts_code} {pick.name}"]

    # 行情数据
    close = data.get("close", pick.close)
    pct_chg = data.get("pct_chg", pick.pct_chg)
    parts.append(f"  收盘 {close}，涨跌幅 {pct_chg}%")

    # 均线
    ma_fields = ["ma5", "ma10", "ma20", "ma60"]
    ma_vals = [f"MA{k[2:]}={data[k]}" for k in ma_fields if data.get(k) is not None]
    if ma_vals:
        parts.append(f"  均线：{', '.join(ma_vals)}")

    # MACD
    if data.get("macd_dif") is not None:
        parts.append(
            f"  MACD：DIF={data['macd_dif']}, DEA={data.get('macd_dea')}, "
            f"HIST={data.get('macd_hist')}"
        )

    # RSI
    if data.get("rsi6") is not None:
        parts.append(f"  RSI6={data['rsi6']}")

    # 量比
    if data.get("vol_ratio") is not None:
        parts.append(f"  量比={data['vol_ratio']}")

    # 基本面
    fundamentals = []
    if data.get("pe_ttm") is not None:
        fundamentals.append(f"PE(TTM)={data['pe_ttm']}")
    if data.get("pb") is not None:
        fundamentals.append(f"PB={data['pb']}")
    if data.get("roe") is not None:
        fundamentals.append(f"ROE={data['roe']}%")
    if data.get("profit_yoy") is not None:
        fundamentals.append(f"利润增速={data['profit_yoy']}%")
    if fundamentals:
        parts.append(f"  基本面：{', '.join(fundamentals)}")

    # 命中策略
    parts.append(f"  命中策略：{', '.join(pick.matched_strategies)}（{pick.match_count}个）")

    return "\n".join(parts)
