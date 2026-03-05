"""LLM 输出解析器：JSON 提取 + Pydantic 验证 + 降级处理。"""

import json
import logging
import re
from typing import Any

from app.research.llm.schema import MacroSignalOutput

logger = logging.getLogger(__name__)

# JSON 提取正则（从 markdown 代码块或裸 JSON 中提取）
_JSON_RE = re.compile(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```|(\{[\s\S]*\})", re.DOTALL)


def extract_json(text: str) -> dict[str, Any] | None:
    """从 LLM 输出文本中提取 JSON 对象。

    支持以下格式：
    - 裸 JSON
    - ```json ... ``` 代码块
    - 混合文字中的 JSON

    Args:
        text: LLM 原始输出

    Returns:
        解析后的字典，失败返回 None
    """
    # 先尝试直接解析
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 从代码块或文本中提取
    match = _JSON_RE.search(text)
    if match:
        json_str = match.group(1) or match.group(2)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # 尝试修复常见 JSON 格式问题
            json_str = json_str.replace("'", '"')  # 单引号 → 双引号
            json_str = re.sub(r",\s*([}\]])", r"\1", json_str)  # 尾部逗号
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

    logger.warning("无法从 LLM 输出中提取 JSON")
    return None


def parse_macro_signal(llm_output: str) -> MacroSignalOutput | None:
    """解析 LLM 输出为 MacroSignalOutput。

    流程：
    1. 提取 JSON
    2. Pydantic 校验
    3. 校验失败时尝试修复
    4. 修复失败返回 None（调用方应降级处理）

    Args:
        llm_output: LLM 原始文本输出

    Returns:
        验证通过的 MacroSignalOutput，失败返回 None
    """
    raw = extract_json(llm_output)
    if raw is None:
        return None

    # 尝试直接解析
    try:
        return MacroSignalOutput.model_validate(raw)
    except Exception as e:
        logger.warning("Pydantic 校验失败（尝试修复）: %s", e)

    # 修复常见问题
    try:
        fixed = _fix_common_issues(raw)
        return MacroSignalOutput.model_validate(fixed)
    except Exception as e:
        logger.error("修复后仍校验失败: %s", e)
        return None


def _fix_common_issues(raw: dict) -> dict:
    """修复 LLM 输出的常见格式问题。"""
    fixed = dict(raw)

    # risk_appetite 规范化
    ra = fixed.get("risk_appetite", "mid")
    ra_map = {"高": "high", "中": "mid", "低": "low", "中等": "mid"}
    fixed["risk_appetite"] = ra_map.get(ra, ra).lower()

    # global_risk_score 范围修正
    score = fixed.get("global_risk_score", 50)
    if isinstance(score, str):
        try:
            score = float(score)
        except ValueError:
            score = 50.0
    fixed["global_risk_score"] = max(0.0, min(100.0, float(score)))

    # key_drivers impact 规范化
    for driver in fixed.get("key_drivers", []):
        impact = driver.get("impact", "neutral")
        impact_map = {"正面": "positive", "负面": "negative", "中性": "neutral"}
        driver["impact"] = impact_map.get(impact, impact).lower()

        mag = driver.get("magnitude", "medium")
        mag_map = {"高": "high", "中": "medium", "低": "low"}
        driver["magnitude"] = mag_map.get(mag, mag).lower()

    return fixed


def build_default_signal() -> MacroSignalOutput:
    """构建默认中性信号（降级用）。"""
    return MacroSignalOutput(
        risk_appetite="mid",
        global_risk_score=50.0,
        positive_sectors=[],
        negative_sectors=[],
        macro_summary="新闻数据不足，无法提取有效宏观信号。默认中性。",
        key_drivers=[],
    )
