"""AI 分析 Prompt 模板。

构建发送给 Gemini 的综合分析提示词。V1 使用单 Prompt 批量分析。
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.strategy.pipeline import StockPick


def build_analysis_prompt(
    picks: list[StockPick],
    market_data: dict[str, dict],
    target_date: date,
) -> str:
    """构建批量股票综合分析 Prompt。

    Args:
        picks: Layer 4 候选股票列表
        market_data: ts_code -> 指标数据字典
        target_date: 分析日期

    Returns:
        完整的分析提示词字符串
    """
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

    return f"""你是一名资深 A 股投资分析师。请对以下 {len(picks)} 只候选股票进行综合分析。

分析日期：{target_date.isoformat()}

候选股票数据：
{stocks_text}

请对每只股票进行以下分析：
1. 技术面：均线排列、MACD 趋势、RSI 超买超卖、量价配合
2. 基本面：估值水平（PE/PB）、盈利能力（ROE）、成长性（利润增速）
3. 综合判断：结合策略命中情况和技术/基本面数据，给出投资建议

请严格按以下 JSON 格式返回，不要包含任何其他文字：
{{
  "analysis": [
    {{
      "ts_code": "股票代码",
      "score": 0到100的整数评分,
      "signal": "STRONG_BUY 或 BUY 或 HOLD 或 SELL 或 STRONG_SELL",
      "reasoning": "简要分析理由（中文，50字以内）"
    }}
  ]
}}

评分标准：
- 90-100：强烈看好，技术面和基本面共振向上
- 70-89：看好，多数指标积极
- 50-69：中性，信号不明确
- 30-49：偏空，存在风险信号
- 0-29：强烈看空，多重风险叠加

注意：必须对每只股票都给出分析，analysis 数组长度必须等于 {len(picks)}。"""


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
