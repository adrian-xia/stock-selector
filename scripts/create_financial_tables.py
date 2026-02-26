#!/usr/bin/env python3
"""创建财务三表业务表（income_statement / balance_sheet / cash_flow_statement）。

使用 CREATE TABLE IF NOT EXISTS，幂等安全。
"""
import asyncio
import sys

sys.path.insert(0, "/Users/adrian/Developer/Codes/stock-selector")

from app.database import engine
from app.models.finance import BalanceSheet, CashFlowStatement, IncomeStatement
from app.models.base import Base


async def main():
    async with engine.begin() as conn:
        for model in (IncomeStatement, BalanceSheet, CashFlowStatement):
            await conn.run_sync(
                lambda sync_conn, m=model: m.__table__.create(sync_conn, checkfirst=True)
            )
            print(f"✓ {model.__tablename__} 已创建（或已存在）")
    print("完成。")


if __name__ == "__main__":
    asyncio.run(main())
