#!/usr/bin/env python3
"""清空生产数据库所有表（保留 alembic_version）。"""
import asyncio
from sqlalchemy import text

async def main():
    from app.database import async_session_factory
    async with async_session_factory() as session:
        result = await session.execute(text(
            "SELECT tablename FROM pg_tables "
            "WHERE schemaname = 'public' "
            "AND tablename <> 'alembic_version' "
            "ORDER BY tablename"
        ))
        tables = [r[0] for r in result.all()]
        print(f"共 {len(tables)} 张表")
        if tables:
            table_list = ", ".join(tables)
            await session.execute(text(f"TRUNCATE {table_list} CASCADE"))
            await session.commit()
            print("✓ 所有表已清空")

if __name__ == "__main__":
    asyncio.run(main())
