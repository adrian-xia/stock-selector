"""行业实体对齐器：LLM 输出行业名 → 系统 sector_code。

将 LLM 返回的自然语言行业名称映射到系统内的同花顺板块代码。
三级降级策略：精确匹配 → 别名匹配 → 模糊匹配 → 标记 unresolved。

V2: 从 sector_mapping.json（DB 导出）加载 467 条映射 + 硬编码别名。
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# --- 加载 sector_mapping.json ---
_MAPPING_FILE = Path(__file__).parent / "sector_mapping.json"

_SECTOR_MAP: dict[str, str] = {}  # name → code
_CODE_TO_NAME: dict[str, str] = {}  # code → canonical name

def _load_mapping() -> None:
    """从 JSON 文件加载行业映射。"""
    global _SECTOR_MAP, _CODE_TO_NAME

    if _MAPPING_FILE.exists():
        with open(_MAPPING_FILE, encoding="utf-8") as f:
            data = json.load(f)

        # THS 板块 (code → name)，反转为 name → code
        for code, name in data.get("ths_sectors", {}).items():
            _SECTOR_MAP[name] = code
            if code not in _CODE_TO_NAME:
                _CODE_TO_NAME[code] = name

        # 申万 L1
        for code, name in data.get("sw_l1", {}).items():
            if name not in _SECTOR_MAP:
                _SECTOR_MAP[name] = code
            if code not in _CODE_TO_NAME:
                _CODE_TO_NAME[code] = name

        # 申万 L2
        for code, name in data.get("sw_l2", {}).items():
            if name not in _SECTOR_MAP:
                _SECTOR_MAP[name] = code
            if code not in _CODE_TO_NAME:
                _CODE_TO_NAME[code] = name

        logger.info("加载行业映射: %d 条 (来源 %s)", len(_SECTOR_MAP), _MAPPING_FILE.name)
    else:
        logger.warning("sector_mapping.json 不存在，使用硬编码别名")

    # 硬编码别名补充（常见缩写 / 同义词，不覆盖 JSON 中已有的映射）
    _ALIASES: dict[str, str] = {
        "芯片": "885736", "集成电路": "885736",
        "AI": "885760", "大模型": "885760",
        "5G": "885740", "光通信": "885740",
        "软件开发": "885756", "计算机": "885756",
        "太阳能": "885724", "风力发电": "885750",
        "动力电池": "885726", "电动车": "885754",
        "酿酒": "885710", "家电": "885714",
        "医疗": "885716", "创新药": "885718",
        "文旅": "885720", "商贸": "885722",
        "券商": "885704", "地产": "885728",
        "有色": "885742",
    }
    for alias, code in _ALIASES.items():
        if alias not in _SECTOR_MAP:
            _SECTOR_MAP[alias] = code
            if code not in _CODE_TO_NAME:
                _CODE_TO_NAME[code] = alias


_load_mapping()


def align_sector(raw_name: str) -> tuple[str | None, str | None]:
    """将 LLM 输出的行业名对齐到系统 sector_code。

    Args:
        raw_name: LLM 原始行业名称

    Returns:
        (sector_code, canonical_name) 或 (None, None) 如果无法对齐
    """
    raw = raw_name.strip()

    # 1. 精确匹配
    if raw in _SECTOR_MAP:
        code = _SECTOR_MAP[raw]
        return code, _CODE_TO_NAME[code]

    # 2. 包含匹配（"新能源汽车产业链" → "新能源汽车"）
    for name, code in _SECTOR_MAP.items():
        if name in raw or raw in name:
            return code, _CODE_TO_NAME[code]

    # 3. 无法对齐
    logger.debug("行业名称未对齐: %s", raw_name)
    return None, None


def align_sectors_batch(
    sector_names: list[str],
) -> list[dict]:
    """批量对齐行业名称。

    Args:
        sector_names: LLM 输出的行业名列表

    Returns:
        对齐结果列表，每项包含 raw_name, sector_code, canonical_name, resolved
    """
    results: list[dict] = []
    unresolved_count = 0

    for name in sector_names:
        code, canonical = align_sector(name)
        results.append({
            "raw_name": name,
            "sector_code": code,
            "canonical_name": canonical,
            "resolved": code is not None,
        })
        if code is None:
            unresolved_count += 1

    if unresolved_count > 0:
        logger.warning(
            "行业对齐: %d/%d 未解析",
            unresolved_count, len(sector_names),
        )

    return results
