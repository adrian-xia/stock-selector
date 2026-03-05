"""LLM Prompt 模板管理。

定义宏观信号提取的 Prompt 模板。
"""

# Prompt 版本号（随模板调整递增，记录到 DB 用于审计）
PROMPT_VERSION = "v1.0"

# 宏观信号提取 Prompt
MACRO_SIGNAL_PROMPT = """你是一位专业的 A 股宏观分析师。请根据以下今日新闻快讯，提取宏观市场信号。

## 新闻内容

{news_text}

## 输出要求

请严格按以下 JSON 格式输出（不要输出 markdown 标记或额外文字）：

{{
  "risk_appetite": "high|mid|low",
  "global_risk_score": 0-100,
  "positive_sectors": [
    {{"sector_name": "行业名称", "reason": "原因", "confidence": 0.0-1.0}}
  ],
  "negative_sectors": [
    {{"sector_name": "行业名称", "reason": "原因", "confidence": 0.0-1.0}}
  ],
  "macro_summary": "1-3句话的宏观摘要",
  "key_drivers": [
    {{"event": "事件", "impact": "positive|negative|neutral", "magnitude": "high|medium|low"}}
  ]
}}

## 评分规则

- `risk_appetite`:
  - "high": 市场情绪积极，政策利好明显，无重大风险事件
  - "mid": 市场信号混合，有利好也有利空
  - "low": 明显利空信号、政策收紧、国际风险事件
- `global_risk_score`: 0=极度恐慌，50=中性，100=极度贪婪
- `sector_name` 使用中文行业名称（如"新能源"、"半导体"、"消费"等）
- `confidence` 基于相关新闻数量和信号强度

## 注意事项

- 只输出与 A 股市场直接相关的分析
- 行业名称使用通用中文名称
- 如果新闻不足以判断，global_risk_score 设为 50，risk_appetite 设为 "mid"
- 确保 JSON 格式正确，可直接解析
"""


def build_macro_prompt(news_items: list[dict], max_tokens: int = 3000) -> str:
    """构建宏观信号提取 Prompt。

    拼接新闻标题 + 内容，截断到 max_tokens 对应的字符上限。

    Args:
        news_items: 清洗后的新闻列表
        max_tokens: LLM 输入 token 上限（1 token ≈ 1.5 中文字）

    Returns:
        完整的 Prompt 文本
    """
    max_chars = int(max_tokens * 1.5)

    # 拼接新闻
    lines: list[str] = []
    total_chars = 0
    for i, item in enumerate(news_items, 1):
        title = item.get("title", "")
        content = item.get("content", "")
        line = f"{i}. {title}"
        if content and content != title:
            # 正文取前 100 字（避免 prompt 过长）
            line += f"  —— {content[:100]}"

        if total_chars + len(line) > max_chars:
            break
        lines.append(line)
        total_chars += len(line)

    news_text = "\n".join(lines)
    return MACRO_SIGNAL_PROMPT.format(news_text=news_text)
