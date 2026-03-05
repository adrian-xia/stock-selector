import asyncio
import logging
import os
from datetime import date
import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.strategy.technical.peak_pullback_stabilization import PeakPullbackStabilizationStrategy
from app.research.scoring.stock_rank_fusion import calc_stock_rank_fusion, RankedStock
from app.research.planner.plan_generator import generate_trade_plans
from app.research.scoring.market_regime import MarketRegimeResult

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DB_URL = "postgresql+asyncpg://postgres:123456@192.168.1.100:5432/stock_selector_prod"


async def fetch_technical_data(session: AsyncSession, trade_date: date) -> pd.DataFrame:
    """Fetch required DataFrame payload for strategy filtering."""
    query = text("""
        SELECT 
            t.ts_code, t.trade_date, t.ma5, t.ma20, t.ma60, t.vol_ma5, t.vol_ma10, t.vol_ratio, t.high_60,
            s.close, s.open, s.vol, s.pct_chg, s.amount, s.turnover_rate,
            i.name as sector_name
        FROM technical_daily t
        JOIN stock_daily s ON t.ts_code = s.ts_code AND t.trade_date = s.trade_date
        LEFT JOIN concept_member m ON s.ts_code = m.stock_code
        LEFT JOIN concept_index i ON m.concept_code = i.ts_code
        WHERE t.trade_date = :td
    """)
    r = await session.execute(query, {"td": trade_date})
    rows = r.fetchall()
    
    if not rows:
        return pd.DataFrame()
        
    df = pd.DataFrame(rows, columns=[
        "ts_code", "trade_date", "ma5", "ma20", "ma60", "vol_ma5", "vol_ma10", "vol_ratio", "high_60",
        "close", "open", "vol", "pct_chg", "amount", "turnover_rate", "sector_name"
    ])
    
    # Cast numeric columns to float to avoid decimal/float type errors
    numeric_cols = ["ma5", "ma20", "ma60", "vol_ma5", "vol_ma10", "vol_ratio", "high_60", 
                    "close", "open", "vol", "pct_chg", "amount", "turnover_rate"]
    for col in numeric_cols:
        df[col] = df[col].astype(float)
    
    # Needs ma5_prev. Since we fetch one day, we must query previous day's MA5 separately
    # For a standalone simple test, let's mock ma5_prev to be slightly lower than ma5 (to satisfy ma5_rising)
    df["ma5_prev"] = df["ma5"] * 0.99
    
    # Deduplicate rows because of the Left Join on concepts
    df = df.drop_duplicates(subset=['ts_code'], keep='first')
        
    df.set_index("ts_code", inplace=True)
    return df


async def test_scenario(
    scenario_name: str, 
    regime: MarketRegimeResult, 
    sector_scores: dict[str, float], 
    picks_df: pd.DataFrame
):
    logger.info("=" * 60)
    logger.info(f"🚀 测试场景: {scenario_name}")
    logger.info(f"🏛️ 市场设为: {regime.market_regime} (risk={regime.risk_score}, cap={regime.position_cap*100}%)")
    
    if picks_df.empty:
        logger.warning("  ⚠️ 今日无形态过滤结果，跳过后续测试。")
        return
        
    # 构建 RankedStock 列表用于传入 planner
    ranked_stocks = []
    
    # Mocking Fusion output based on picks
    for ts_code, row in picks_df.head(5).iterrows():
        # Fake Fusion details (Since we isolate planner testing)
        sec_name = row.get("sector_name", "") or ""
        sec_score = sector_scores.get(sec_name, 50.0)
        
        ranked_stocks.append(RankedStock(
            ts_code=str(ts_code),
            stock_rank=95.0, # Mock final rank
            strategy_score_n=100.0,
            sector_score_n=sec_score,
            moneyflow_score_n=80.0,
            liquidity_score_n=80.0,
            source_strategies=["peak-pullback-stabilization"],
            sector_name=str(sec_name)
        ))
        
    # Generate plans
    plans = generate_trade_plans(
        ranked_stocks=ranked_stocks,
        market_regime=regime,
        sector_scores=sector_scores,
        trade_date=date.today(),
        max_plans=5
    )
    
    for p in plans:
        logger.info(f"  ✅ 计划生成: {p['ts_code']}")
        logger.info(f"     => Type: {p['plan_type']}")
        logger.info(f"     => Entry Rule: {p['entry_rule']}")
        logger.info(f"     => Stop/Profit: 损={p['stop_loss_rule']} | 盈={p['take_profit_rule']}")
        logger.info(f"     => Position: {float(p['position_suggestion'])}% (Cap constrained: {float(regime.position_cap)*100}%)")
        logger.info(f"     => Risk Flags: {p['risk_flags']}")
    
    if not plans and regime.risk_score > 70:
         logger.info("  🛡️ 触发了极高风险被阻断生成，测试通过。")


async def main():
    engine = create_async_engine(DB_URL)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # 尝试找一个有结果的日期，或者直接构造一份假 DataFrame
    picks = pd.DataFrame()
    async with session_factory() as session:
        for offset in range(10):
            td = date(2026, 3, 5).replace(day=5-offset) if 5-offset > 0 else date(2026, 2, 28-offset)
            logger.info(f"📥 获取 {td} 全市场量价数据以测算策略...")
            df = await fetch_technical_data(session, td)
            if df.empty:
                continue
                
            strategy = PeakPullbackStabilizationStrategy()
            # Relax constraints locally to force some results for testing purposes
            strategy.params["min_pullback_pct"] = 5.0
            strategy.params["max_vol_ratio"] = 1.2
            
            mask = await strategy.filter_batch(df, td)
            picks = df[mask]
            if not picks.empty:
                logger.info(f"🎉 日期 {td} 策略初筛命中: {len(picks)} 只股票")
                break
        
        if picks.empty:
            logger.warning("连续几日无真实命中，使用前排几只股票强行 Mock")
            if not df.empty:
                picks = df.head(5)
    
    # 场景A：顺风局 (Bullish) - 行业有共振，大盘没风险
    await test_scenario(
        scenario_name="场景A：顺风局 (Bullish/Mid Risk)",
        regime=MarketRegimeResult(
            market_regime="bull", risk_score=20.0, position_cap=0.9,
            volatility_risk=20, trend_risk=20, breadth_risk=20, sentiment_risk=20, details={}
        ),
        sector_scores={"半导体": 90.0, "人工智能": 85.0}, # Mock positive sectors
        picks_df=picks
    )
    
    # 场景B：逆风局 (Bearish) - 大盘高风险，强制减仓或禁止
    await test_scenario(
        scenario_name="场景B：极高风险局 (Bearish/High Risk)",
        regime=MarketRegimeResult(
            market_regime="bear", risk_score=85.0, position_cap=0.3,
            volatility_risk=80, trend_risk=90, breadth_risk=80, sentiment_risk=90, details={}
        ),
        sector_scores={},
        picks_df=picks
    )
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
