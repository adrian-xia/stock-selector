"""个股融合排序（Stock Rank Fusion）。

融合策略分、行业分、资金分、流动性分，输出最终排名。
算法来源：设计文档 §6.3。

权重（V1）：
  stock_rank = 0.50*strategy_score_n + 0.25*sector_score_n
             + 0.15*moneyflow_score_n + 0.10*liquidity_score_n
"""

import logging
from dataclasses import dataclass
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.research.scoring.normalize import percentile_rank

logger = logging.getLogger(__name__)


@dataclass
class RankedStock:
    """融合排名后的个股。"""

    ts_code: str
    stock_rank: float  # 最终融合分 0~100
    strategy_score_n: float  # 策略分（归一化）
    sector_score_n: float  # 行业分（归一化）
    moneyflow_score_n: float  # 资金分（归一化）
    liquidity_score_n: float  # 流动性分（归一化）
    source_strategies: list[str]  # 命中的策略列表
    sector_name: str  # 所属行业
    close: float  # 当日收盘价


async def calc_stock_rank_fusion(
    session_factory: async_sessionmaker[AsyncSession],
    trade_date: date,
    sector_scores: dict[str, float] | None = None,
    top_n: int = 30,
) -> list[RankedStock]:
    """计算个股融合排序。

    从 strategy_picks 获取当日选股结果，结合行业评分、
    资金流和换手率进行横截面归一化和加权排名。

    Args:
        session_factory: 数据库会话工厂
        trade_date: 交易日
        sector_scores: {sector_code: final_score} 行业评分字典
        top_n: 返回前 N 只

    Returns:
        按 stock_rank 降序排列的排名列表
    """
    sector_scores = sector_scores or {}

    async with session_factory() as session:
        # 1. 获取当日策略选股结果
        try:
            rows = await session.execute(
                text(
                    "SELECT ts_code, strategy_name, pick_score, pick_close "
                    "FROM strategy_picks "
                    "WHERE pick_date = :td "
                    "ORDER BY pick_score DESC"
                ),
                {"td": trade_date},
            )
            picks = rows.fetchall()
        except Exception:
            logger.error("[个股融合] 获取选股结果失败", exc_info=True)
            return []

        if not picks:
            logger.info("[个股融合] %s: 无选股结果", trade_date)
            return []

        # 聚合：每只股票的策略分 = max(pick_score)，策略列表
        stock_data: dict[str, dict] = {}
        for r in picks:
            code = r.ts_code
            if code not in stock_data:
                stock_data[code] = {
                    "strategy_score": float(r.pick_score or 0),
                    "strategies": [r.strategy_name],
                    "close": float(r.pick_close or 0),
                }
            else:
                stock_data[code]["strategy_score"] = max(
                    stock_data[code]["strategy_score"],
                    float(r.pick_score or 0),
                )
                if r.strategy_name not in stock_data[code]["strategies"]:
                    stock_data[code]["strategies"].append(r.strategy_name)
                if not stock_data[code].get("close") and r.pick_close is not None:
                    stock_data[code]["close"] = float(r.pick_close or 0)

        codes = list(stock_data.keys())

        # 2. 获取资金流和换手率
        try:
            placeholders = ",".join([f":c{i}" for i in range(len(codes))])
            params = {"td": trade_date}
            params.update({f"c{i}": c for i, c in enumerate(codes)})

            rows = await session.execute(
                text(
                    f"SELECT ts_code, turnover_rate, amount "
                    f"FROM stock_daily "
                    f"WHERE trade_date = :td AND ts_code IN ({placeholders})"
                ),
                params,
            )
            for r in rows:
                if r.ts_code in stock_data:
                    stock_data[r.ts_code]["turnover"] = float(r.turnover_rate or 0)
                    stock_data[r.ts_code]["amount"] = float(r.amount or 0)
        except Exception:
            logger.warning("[个股融合] 资金/换手数据查询失败", exc_info=True)

        # 3. 获取行业归属
        try:
            rows = await session.execute(
                text(
                    f"SELECT cm.ts_code, ci.ts_code AS sector_code, ci.name AS sector_name "
                    f"FROM concept_member cm "
                    f"JOIN concept_index ci ON cm.concept_code = ci.ts_code "
                    f"WHERE cm.ts_code IN ({placeholders})"
                ),
                params,
            )
            for r in rows:
                if r.ts_code in stock_data:
                    stock_data[r.ts_code]["sector_code"] = r.sector_code
                    stock_data[r.ts_code]["sector_name"] = r.sector_name
        except Exception:
            pass

    # 4. 全市场 percentile rank 归一化
    all_codes = list(stock_data.keys())
    strategy_scores_raw = [stock_data[c].get("strategy_score", 0) for c in all_codes]
    moneyflow_raw = [stock_data[c].get("amount", 0) for c in all_codes]
    liquidity_raw = [stock_data[c].get("turnover", 0) for c in all_codes]

    # 行业分：从 sector_scores 映射
    sector_raw = []
    for c in all_codes:
        sc = stock_data[c].get("sector_code", "")
        sector_raw.append(sector_scores.get(sc, 50.0))

    strategy_n = percentile_rank(strategy_scores_raw)
    sector_n = percentile_rank(sector_raw)
    moneyflow_n = percentile_rank(moneyflow_raw)
    liquidity_n = percentile_rank(liquidity_raw)

    # 5. 加权融合
    results: list[RankedStock] = []
    for i, code in enumerate(all_codes):
        rank = (
            0.50 * strategy_n[i]
            + 0.25 * sector_n[i]
            + 0.15 * moneyflow_n[i]
            + 0.10 * liquidity_n[i]
        )
        results.append(RankedStock(
            ts_code=code,
            stock_rank=round(rank, 2),
            strategy_score_n=strategy_n[i],
            sector_score_n=sector_n[i],
            moneyflow_score_n=moneyflow_n[i],
            liquidity_score_n=liquidity_n[i],
            source_strategies=stock_data[code].get("strategies", []),
            sector_name=stock_data[code].get("sector_name", ""),
            close=float(stock_data[code].get("close", 0) or 0),
        ))

    # 按 rank 降序
    results.sort(key=lambda r: r.stock_rank, reverse=True)

    logger.info(
        "[个股融合] %s: %d 只股票排名，Top3: %s",
        trade_date, len(results),
        [(r.ts_code, round(r.stock_rank, 1)) for r in results[:3]],
    )

    return results[:top_n]
