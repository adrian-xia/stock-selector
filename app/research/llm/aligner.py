"""行业实体对齐器：LLM 输出行业名 → 系统 sector_code。

将 LLM 返回的自然语言行业名称映射到系统内的同花顺板块代码。
三级降级策略：精确匹配 → 别名匹配 → 模糊匹配 → 标记 unresolved。
"""

import logging

logger = logging.getLogger(__name__)

# 行业名 → sector_code 静态映射（V1: 硬编码主要行业）
# 后续 Phase 1.8 从 concept_index 表导出完整映射
_SECTOR_MAP: dict[str, str] = {
    # 科技
    "半导体": "885736",
    "芯片": "885736",
    "集成电路": "885736",
    "人工智能": "885760",
    "AI": "885760",
    "大模型": "885760",
    "云计算": "885768",
    "软件": "885756",
    "软件开发": "885756",
    "计算机": "885756",
    "消费电子": "885738",
    "电子": "885738",
    "通信": "885740",
    "5G": "885740",
    "光通信": "885740",
    # 新能源
    "新能源": "885748",
    "光伏": "885724",
    "太阳能": "885724",
    "风电": "885750",
    "风力发电": "885750",
    "储能": "885752",
    "锂电池": "885726",
    "动力电池": "885726",
    "新能源汽车": "885754",
    "电动车": "885754",
    # 消费
    "消费": "885708",
    "白酒": "885710",
    "酿酒": "885710",
    "食品饮料": "885712",
    "食品": "885712",
    "家电": "885714",
    "家用电器": "885714",
    "医药": "885716",
    "医疗": "885716",
    "生物医药": "885718",
    "创新药": "885718",
    "旅游": "885720",
    "文旅": "885720",
    "零售": "885722",
    "商贸": "885722",
    # 金融
    "银行": "885702",
    "券商": "885704",
    "证券": "885704",
    "保险": "885706",
    "金融科技": "885762",
    # 周期
    "房地产": "885728",
    "地产": "885728",
    "建筑": "885730",
    "建材": "885732",
    "钢铁": "885734",
    "有色金属": "885742",
    "有色": "885742",
    "煤炭": "885744",
    "石油": "885746",
    "化工": "885764",
    # 其他
    "军工": "885758",
    "国防军工": "885758",
    "汽车": "885766",
    "农业": "885770",
    "环保": "885772",
    "交通运输": "885774",
    "物流": "885774",
    "电力": "885776",
    "公用事业": "885776",
    "传媒": "885778",
    "教育": "885780",
}

# 反向映射 sector_code → 标准名称（取第一个注册的名称）
_CODE_TO_NAME: dict[str, str] = {}
for name, code in _SECTOR_MAP.items():
    if code not in _CODE_TO_NAME:
        _CODE_TO_NAME[code] = name


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
