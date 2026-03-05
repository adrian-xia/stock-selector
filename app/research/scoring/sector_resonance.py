"""行业共振评分（Sector Resonance）。

融合新闻面、资金面、趋势面三维度评分，输出行业共振排名。
算法来源：设计文档 §6.2。

权重（V1）：
  final_score = 0.20*news_score + 0.45*moneyflow_score + 0.35*trend_score
"""

import logging
from dataclasses import dataclass
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


@dataclass
class SectorScore:
    """单个行业的共振评分。"""

    sector_code: str
    sector_name: str
    news_score: float  # 0~100
    moneyflow_score: float  # 0~100
    trend_score: float  # 0~100
    final_score: float  # 加权总分
    confidence: float  # 0~100
    drivers: list[str]  # 驱动因素


async def calc_sector_resonance(
    session_factory: async_sessionmaker[AsyncSession],
    trade_date: date,
    macro_positive_sectors: list[dict] | None = None,
    macro_negative_sectors: list[dict] | None = None,
) -> list[SectorScore]:
    """计算行业共振评分。

    Args:
        session_factory: 数据库会话工厂
        trade_date: 交易日
        macro_positive_sectors: LLM 提取的利好行业（含 sector_code）
        macro_negative_sectors: LLM 提取的利空行业（含 sector_code）

    Returns:
        按 final_score 降序排列的行业评分列表
    """
    positive_codes = set()
    negative_codes = set()
    if macro_positive_sectors:
        positive_codes = {s.get("sector_code", "") for s in macro_positive_sectors if s.get("sector_code")}
    if macro_negative_sectors:
        negative_codes = {s.get("sector_code", "") for s in macro_negative_sectors if s.get("sector_code")}

    sectors: dict[str, SectorScore] = {}

    async with session_factory() as session:
        # ---- 1. 从板块数据获取趋势和资金分 ----
        try:
            rows = await session.execute(
                text(
                    "SELECT ci.ts_code, ci.name, cd.pct_change, cd.turnover_rate, "
                    "       cd.amount "
                    "FROM concept_daily cd "
                    "JOIN concept_index ci ON cd.ts_code = ci.ts_code "
                    "WHERE cd.trade_date = :td"
                ),
                {"td": trade_date.strftime("%Y%m%d")},
            )

            all_rows = rows.fetchall()
            if not all_rows:
                logger.warning("[行业共振] 无板块数据: %s", trade_date)
                return []

            # 收集原始数据用于归一化
            pct_changes = [float(r.pct_change or 0) for r in all_rows]
            amounts = [float(r.amount or 0) for r in all_rows]

            pct_min = min(pct_changes) if pct_changes else 0
            pct_max = max(pct_changes) if pct_changes else 1
            pct_range = max(pct_max - pct_min, 0.01)

            amt_min = min(amounts) if amounts else 0
            amt_max = max(amounts) if amounts else 1
            amt_range = max(amt_max - amt_min, 0.01)

            for r in all_rows:
                code = r.ts_code
                name = r.name
                pct = float(r.pct_change or 0)
                amount = float(r.amount or 0)

                # 趋势分：min-max 归一化到 0~100
                trend_score = ((pct - pct_min) / pct_range) * 100

                # 资金分：成交额 min-max 归一化到 0~100
                moneyflow_score = ((amount - amt_min) / amt_range) * 100

                # 新闻分：基于宏观信号
                news_score = 50.0  # 默认中性
                drivers: list[str] = []

                if code in positive_codes:
                    news_score = 80.0
                    drivers.append("LLM利好")
                elif code in negative_codes:
                    news_score = 20.0
                    drivers.append("LLM利空")

                # V1 权重
                final_score = (
                    0.20 * news_score
                    + 0.45 * moneyflow_score
                    + 0.35 * trend_score
                )

                # 置信度
                data_completeness = 100.0  # 有板块数据即认为完整
                if code in positive_codes or code in negative_codes:
                    signal_consistency = 80.0
                else:
                    signal_consistency = 60.0
                confidence = min(100.0, 0.6 * data_completeness + 0.4 * signal_consistency)

                sectors[code] = SectorScore(
                    sector_code=code,
                    sector_name=name,
                    news_score=round(news_score, 2),
                    moneyflow_score=round(moneyflow_score, 2),
                    trend_score=round(trend_score, 2),
                    final_score=round(final_score, 2),
                    confidence=round(confidence, 2),
                    drivers=drivers,
                )

        except Exception:
            logger.error("[行业共振] 计算失败", exc_info=True)
            return []

    # 按 final_score 降序排序
    result = sorted(sectors.values(), key=lambda s: s.final_score, reverse=True)

    logger.info(
        "[行业共振] %s: %d 个行业，Top3: %s",
        trade_date, len(result),
        [(s.sector_name, round(s.final_score, 1)) for s in result[:3]],
    )
    return result
