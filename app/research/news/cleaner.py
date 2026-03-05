"""新闻清洗：去 HTML、截断正文、字段标准化。"""

import re

# HTML 标签 + 实体清理
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_HTML_ENTITY_RE = re.compile(r"&[a-zA-Z]+;|&#\d+;")

# 连续空白压缩
_MULTI_SPACE_RE = re.compile(r"\s+")

# 最大正文长度（LLM 输入限制考虑）
MAX_CONTENT_LENGTH = 2000


def clean_html(text: str) -> str:
    """去除 HTML 标签和实体。"""
    text = _HTML_TAG_RE.sub("", text)
    text = _HTML_ENTITY_RE.sub("", text)
    return text.strip()


def normalize_whitespace(text: str) -> str:
    """压缩连续空白为单个空格。"""
    return _MULTI_SPACE_RE.sub(" ", text).strip()


def truncate(text: str, max_length: int = MAX_CONTENT_LENGTH) -> str:
    """截断过长文本，保留整句。"""
    if len(text) <= max_length:
        return text

    # 尝试在句号/问号/感叹号处截断
    truncated = text[:max_length]
    for sep in ("。", "！", "？", ".", "!", "?"):
        idx = truncated.rfind(sep)
        if idx > max_length * 0.5:  # 至少保留 50%
            return truncated[: idx + 1]

    return truncated + "…"


def clean_news_item(item: dict) -> dict:
    """清洗单条新闻。

    处理步骤：
    1. 去 HTML 标签和实体
    2. 压缩空白
    3. 截断过长正文
    4. 确保必要字段存在

    Args:
        item: 原始新闻字典

    Returns:
        清洗后的新闻字典
    """
    cleaned = dict(item)

    # 清洗标题
    title = cleaned.get("title", "")
    title = clean_html(title)
    title = normalize_whitespace(title)
    cleaned["title"] = title[:200]  # 标题限制 200 字

    # 清洗正文
    content = cleaned.get("content", "")
    content = clean_html(content)
    content = normalize_whitespace(content)
    cleaned["content"] = truncate(content)

    return cleaned


def clean_news_batch(items: list[dict]) -> list[dict]:
    """批量清洗新闻列表，过滤无效条目。

    Args:
        items: 原始新闻列表

    Returns:
        清洗后的有效新闻列表
    """
    result: list[dict] = []
    for item in items:
        cleaned = clean_news_item(item)
        # 过滤空标题或过短内容
        if len(cleaned["title"]) < 5 or len(cleaned["content"]) < 10:
            continue
        result.append(cleaned)
    return result
