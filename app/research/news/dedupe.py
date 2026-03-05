"""新闻去重：基于 Jaccard 分词相似度。

使用 jieba 分词 + Jaccard 系数进行近似去重，阈值 0.7。
"""

import hashlib
import logging

logger = logging.getLogger(__name__)

# Jaccard 相似度阈值（≥ 此值视为重复）
SIMILARITY_THRESHOLD = 0.7


def _tokenize(text: str) -> set[str]:
    """中文分词。优先使用 jieba，不可用时按字符切分。"""
    try:
        import jieba
        return set(jieba.lcut(text))
    except ImportError:
        # 降级：按 bigram 切分
        tokens: set[str] = set()
        for i in range(len(text) - 1):
            tokens.add(text[i : i + 2])
        return tokens


def _jaccard(a: set[str], b: set[str]) -> float:
    """计算两个集合的 Jaccard 相似度。"""
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union > 0 else 0.0


def content_hash(text: str) -> str:
    """计算文本的 SHA-256 哈希。"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def dedupe_news(items: list[dict], text_key: str = "content") -> list[dict]:
    """去重新闻列表。

    两阶段去重：
    1. 精确去重：content_hash 完全相同
    2. 近似去重：Jaccard 分词相似度 ≥ 阈值

    Args:
        items: 新闻字典列表
        text_key: 文本字段名

    Returns:
        去重后的新闻列表（保留首次出现的）
    """
    if not items:
        return []

    # 阶段 1：精确去重
    seen_hashes: set[str] = set()
    stage1: list[dict] = []
    for item in items:
        text = item.get(text_key, "")
        h = content_hash(text)
        if h not in seen_hashes:
            seen_hashes.add(h)
            item["content_hash"] = h
            stage1.append(item)

    # 阶段 2：近似去重（O(n²)，但 n 通常 < 200）
    tokenized: list[tuple[dict, set[str]]] = [
        (item, _tokenize(item.get(text_key, "")))
        for item in stage1
    ]

    result: list[dict] = []
    kept_tokens: list[set[str]] = []

    for item, tokens in tokenized:
        is_dup = False
        for kept in kept_tokens:
            if _jaccard(tokens, kept) >= SIMILARITY_THRESHOLD:
                is_dup = True
                break
        if not is_dup:
            result.append(item)
            kept_tokens.append(tokens)

    removed = len(items) - len(result)
    if removed > 0:
        logger.info("新闻去重: %d → %d（移除 %d 条）", len(items), len(result), removed)

    return result
