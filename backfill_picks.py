import asyncio
from app.database import async_session_factory, get_raw_connection
from app.strategy.pipeline import execute_pipeline
from app.strategy.factory import StrategyFactory

async def backfill():
    # 获取 60 个交易日
    async with get_raw_connection() as conn:
        rows = await conn.fetch("""
            SELECT DISTINCT cal_date FROM trade_calendar 
            WHERE is_open = true AND cal_date <= '2026-02-26'
            ORDER BY cal_date DESC LIMIT 60
        """)
    trade_dates = sorted([r['cal_date'] for r in rows])
    
    # 获取所有策略名
    all_strategies = [s.name for s in StrategyFactory.get_all()]
    print(f"策略数: {len(all_strategies)}, 交易日数: {len(trade_dates)}")
    
    for i, td in enumerate(trade_dates):
        try:
            result = await execute_pipeline(
                session_factory=async_session_factory,
                strategy_names=all_strategies,
                top_n=50,
                target_date=td,
            )
            picks_count = len(result.picks) if hasattr(result, 'picks') else 0
            print(f"  [{i+1}/60] {td}: {picks_count} picks, {result.elapsed_ms}ms")
        except Exception as e:
            print(f"  [{i+1}/60] {td}: ❌ {e}")

asyncio.run(backfill())
