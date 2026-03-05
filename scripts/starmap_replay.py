"""StarMap 历史回放脚本 (Phase 4.1 + 4.2)。

用生产库历史数据 + mock 新闻，验证评分引擎和计划生成链路。
不调用 LLM，直接注入 mock MacroSignalOutput。

用法：
    DATABASE_URL="postgresql+asyncpg://postgres:123456@192.168.1.100:5432/stock_selector_prod" \
    uv run python scripts/starmap_replay.py
"""

import asyncio
import logging
import sys
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---- 评分引擎 ----
from app.research.scoring.market_regime import calc_market_regime
from app.research.scoring.normalize import percentile_rank, normalize_scores
from app.research.scoring.stock_rank_fusion import calc_stock_rank_fusion
from app.research.llm.schema import MacroSignalOutput, SectorImpact
from app.research.planner.plan_generator import generate_trade_plans

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DB_URL = "postgresql+asyncpg://postgres:123456@192.168.1.100:5432/stock_selector_prod"

# --- Mock 宏观信号 ---
MOCK_SIGNALS: dict[str, MacroSignalOutput] = {
    "bullish": MacroSignalOutput(
        risk_appetite="high",
        global_risk_score=75.0,
        positive_sectors=[
            SectorImpact(sector_name="半导体", reason="政策利好", confidence=0.9),
            SectorImpact(sector_name="新能源", reason="需求旺盛", confidence=0.8),
        ],
        negative_sectors=[
            SectorImpact(sector_name="房地产", reason="调控加紧", confidence=0.7),
        ],
        macro_summary="市场情绪偏多，科技板块受政策利好驱动",
        key_drivers=[],
    ),
    "neutral": MacroSignalOutput(
        risk_appetite="mid",
        global_risk_score=50.0,
        positive_sectors=[],
        negative_sectors=[],
        macro_summary="市场整体中性，无明显方向",
        key_drivers=[],
    ),
    "bearish": MacroSignalOutput(
        risk_appetite="low",
        global_risk_score=25.0,
        positive_sectors=[],
        negative_sectors=[
            SectorImpact(sector_name="银行", reason="利率下行", confidence=0.8),
        ],
        macro_summary="市场风险偏低，防御为主",
        key_drivers=[],
    ),
}


async def get_trade_dates(session: AsyncSession, n: int = 5) -> list[date]:
    """获取最近 n 个交易日。"""
    r = await session.execute(text("""
        SELECT DISTINCT trade_date FROM stock_daily
        WHERE trade_date <= CURRENT_DATE
        ORDER BY trade_date DESC
        LIMIT :n
    """), {"n": n})
    return [row[0] for row in r.fetchall()][::-1]


async def get_index_data(session: AsyncSession, trade_date: date) -> dict:
    """获取指数数据（上证+创业板）。"""
    r = await session.execute(text("""
        SELECT ts_code, close, pct_chg, vol, amount
        FROM index_daily
        WHERE trade_date = :td AND ts_code IN ('000001.SH', '399006.SZ', '000300.SH')
    """), {"td": trade_date})
    rows = r.fetchall()
    return {row[0]: {"close": float(row[1]), "pct_chg": float(row[2]), "vol": float(row[3]), "amount": float(row[4])} for row in rows}


async def get_top_stocks(session: AsyncSession, trade_date: date, limit: int = 50) -> list[dict]:
    """获取当日成交额 Top N 股票。"""
    r = await session.execute(text("""
        SELECT s.ts_code, s.close, s.pct_chg, s.vol, s.amount, s.turnover_rate
        FROM stock_daily s
        WHERE s.trade_date = :td AND s.close > 0 AND s.amount > 0
        ORDER BY s.amount DESC
        LIMIT :limit
    """), {"td": trade_date, "limit": limit})
    return [
        {
            "ts_code": row[0],
            "close": float(row[1]),
            "pct_chg": float(row[2]),
            "vol": float(row[3]),
            "amount": float(row[4]),
            "turnover_rate": float(row[5]) if row[5] else 0.0,
        }
        for row in r.fetchall()
    ]


async def get_market_breadth(session: AsyncSession, trade_date: date) -> dict:
    """计算市场宽度（涨跌比例）。"""
    r = await session.execute(text("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN pct_chg > 0 THEN 1 ELSE 0 END) as up,
            SUM(CASE WHEN pct_chg < 0 THEN 1 ELSE 0 END) as down,
            AVG(pct_chg) as avg_chg
        FROM stock_daily
        WHERE trade_date = :td AND close > 0
    """), {"td": trade_date})
    row = r.fetchone()
    total = int(row[0]) if row[0] else 1
    return {
        "total": total,
        "up": int(row[1]) if row[1] else 0,
        "down": int(row[2]) if row[2] else 0,
        "up_ratio": (int(row[1]) / total * 100) if row[1] and total else 50.0,
        "avg_chg": float(row[3]) if row[3] else 0.0,
    }


async def replay_one_day(session_factory, session: AsyncSession, trade_date: date, signal_type: str = "neutral") -> dict:
    """回放单日 StarMap 评分链路。"""
    logger.info("=" * 60)
    logger.info("📅 回放日期: %s (信号类型: %s)", trade_date, signal_type)

    # 1. 获取市场数据
    index_data = await get_index_data(session, trade_date)
    breadth = await get_market_breadth(session, trade_date)
    top_stocks = await get_top_stocks(session, trade_date, limit=50)

    if not index_data:
        logger.warning("  ⚠️ 无指数数据，跳过")
        return {"trade_date": str(trade_date), "status": "skipped", "reason": "no_index_data"}

    sh_data = index_data.get("000001.SH", {})
    logger.info("  📊 上证: %.2f (%.2f%%), 涨跌比: %d/%d (%.1f%%)",
                sh_data.get("close", 0), sh_data.get("pct_chg", 0),
                breadth["up"], breadth["down"], breadth["up_ratio"])

    # 2. 市场状态评分
    regime = await calc_market_regime(session_factory, trade_date)
    logger.info("  🏛️  市场状态: %s (risk=%.1f, cap=%.0f%%)",
                regime.market_regime, regime.risk_score, regime.position_cap * 100)

    # 3. 个股融合排序
    mock_signal = MOCK_SIGNALS[signal_type]
    
    # 构建一个假的 sector_scores 字典用于测试 (默认全部 50分，符合正向信号的给 90 分)
    sector_scores_mock = {}
    for pos_sector in mock_signal.positive_sectors:
        # Mocking an arbitrary sector code mapping for positive sectors
        sector_scores_mock["885736"] = 90.0 # Just testing the pass through
    
    ranked_stocks = await calc_stock_rank_fusion(
        session_factory, 
        trade_date, 
        sector_scores=sector_scores_mock, 
        top_n=5
    )

    if not ranked_stocks:
         logger.warning("  ⚠️ 无选股结果，跳过")
         return {"trade_date": str(trade_date), "status": "skipped", "reason": "no_stock_picks"}

    logger.info("  🏆 Top %d 排名:", len(ranked_stocks))
    for i, r in enumerate(ranked_stocks, 1):
        logger.info("     %d. %s  final=%.1f (strategy=%.1f, sector=%.1f)",
                     i, r.ts_code, r.stock_rank,
                     r.strategy_score_n, r.sector_score_n)

    # 4. 生成交易计划
    # `generate_trade_plans` expects a list of RankedStock exactly as returned by calc_stock_rank_fusion
    plans = generate_trade_plans(
        ranked_stocks=ranked_stocks,
        market_regime=regime,
        sector_scores=sector_scores_mock,
        trade_date=trade_date,
        max_plans=5,
    )

    logger.info("  📋 生成交易计划: %d 条", len(plans))
    for p in plans[:3]:
        logger.info("     %s | type=%s | pos=%.0f%% | entry=%s",
                     p.get("ts_code"), p.get("plan_type"),
                     p.get("position_suggestion", 0) * 100,
                     p.get("entry_rule", "")[:40])

    return {
        "trade_date": str(trade_date),
        "status": "success",
        "signal_type": signal_type,
        "regime": regime.market_regime,
        "risk_score": regime.risk_score,
        "position_cap": regime.position_cap,
        "breadth": breadth,
        "top5": [s.ts_code for s in ranked_stocks[:5]],
        "plan_count": len(plans),
    }


async def main():
    engine = create_async_engine(DB_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        # 获取最近 5 个交易日
        trade_dates = await get_trade_dates(session, n=5)
        logger.info("🎯 回放交易日: %s", [str(d) for d in trade_dates])

        results = []
        signal_types = ["bullish", "neutral", "bearish", "bullish", "neutral"]

        for i, td in enumerate(trade_dates):
            sig = signal_types[i % len(signal_types)]
            result = await replay_one_day(session_factory, session, td, sig)
            results.append(result)

    await engine.dispose()

    # 汇总
    logger.info("\n" + "=" * 60)
    logger.info("📊 回放汇总 (%d 日)", len(results))
    logger.info("-" * 60)
    for r in results:
        if r["status"] == "success":
            logger.info("  %s | %s | risk=%.1f | cap=%.0f%% | plans=%d | top=%s",
                        r["trade_date"], r["regime"], r["risk_score"],
                        r["position_cap"] * 100, r["plan_count"],
                        ",".join(r["top5"][:3]))
        else:
            logger.info("  %s | %s", r["trade_date"], r["status"])


if __name__ == "__main__":
    asyncio.run(main())
