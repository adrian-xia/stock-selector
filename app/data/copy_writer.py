"""PostgreSQL COPY 协议批量写入模块。

使用 asyncpg 的 copy_records_to_table() 实现高性能批量写入，
采用临时表 + COPY + UPSERT 三步法保证幂等性。

写入流程：
1. 创建与目标表同结构的临时表（ON COMMIT DROP）
2. 通过 COPY 协议将数据写入临时表
3. 从临时表 INSERT INTO 目标表（ON CONFLICT DO UPDATE/NOTHING）

性能提升约 10 倍（相比逐行 INSERT）。
"""

import logging
import time
from typing import Literal

from sqlalchemy import Table

from app.database import get_raw_connection

logger = logging.getLogger(__name__)

# 单次 COPY 最大行数（控制内存使用）
COPY_BATCH_SIZE = 50000


async def copy_insert(
    table: Table,
    rows: list[dict],
    conflict: Literal["update", "nothing"] = "nothing",
    batch_size: int = COPY_BATCH_SIZE,
) -> int:
    """使用 COPY 协议批量写入数据到目标表。

    采用临时表 + COPY + UPSERT 三步法，兼顾高性能和幂等性。

    Args:
        table: SQLAlchemy Table 对象
        rows: 待写入的数据行列表
        conflict: 冲突处理策略
            - "update": ON CONFLICT DO UPDATE（适用于 raw 表）
            - "nothing": ON CONFLICT DO NOTHING（适用于业务表）
        batch_size: 单次 COPY 最大行数，默认 50000

    Returns:
        处理的总行数

    Raises:
        Exception: COPY 操作失败时抛出，调用方应捕获并降级
    """
    if not rows:
        return 0

    total = len(rows)
    start = time.monotonic()
    table_name = table.name

    # 获取列信息
    columns = [c.name for c in table.columns]
    pk_cols = [c.name for c in table.primary_key.columns]

    processed = 0

    async with get_raw_connection() as raw_conn:
        # 分批处理
        for offset in range(0, total, batch_size):
            batch = rows[offset : offset + batch_size]
            batch_start = time.monotonic()

            # 将 dict 列表转为 tuple 列表（按列顺序）
            records = [
                tuple(row.get(col) for col in columns)
                for row in batch
            ]

            tmp_table = f"_tmp_{table_name}"

            # 1. 创建临时表（与目标表同结构）
            await raw_conn.execute(
                f'CREATE TEMP TABLE "{tmp_table}" '
                f'(LIKE "{table_name}" INCLUDING DEFAULTS) '
                f"ON COMMIT DROP"
            )

            try:
                # 2. COPY 数据到临时表
                await raw_conn.copy_records_to_table(
                    tmp_table,
                    records=records,
                    columns=columns,
                )

                # 3. 从临时表 UPSERT 到目标表
                col_list = ", ".join(f'"{c}"' for c in columns)
                insert_sql = (
                    f'INSERT INTO "{table_name}" ({col_list}) '
                    f'SELECT {col_list} FROM "{tmp_table}" '
                )

                if conflict == "update" and pk_cols:
                    # ON CONFLICT DO UPDATE（raw 表模式）
                    pk_list = ", ".join(f'"{c}"' for c in pk_cols)
                    update_cols = [
                        c for c in columns
                        if c not in pk_cols and c != "fetched_at"
                    ]
                    if update_cols:
                        set_clause = ", ".join(
                            f'"{c}" = EXCLUDED."{c}"' for c in update_cols
                        )
                        insert_sql += (
                            f"ON CONFLICT ({pk_list}) "
                            f"DO UPDATE SET {set_clause}"
                        )
                    else:
                        insert_sql += (
                            f"ON CONFLICT ({pk_list}) DO NOTHING"
                        )
                elif pk_cols:
                    # ON CONFLICT DO NOTHING（业务表模式）
                    pk_list = ", ".join(f'"{c}"' for c in pk_cols)
                    insert_sql += (
                        f"ON CONFLICT ({pk_list}) DO NOTHING"
                    )

                await raw_conn.execute(insert_sql)

                # 清理临时表（ON COMMIT DROP 在事务提交时清理，
                # 但显式 DROP 确保同一事务内多批次不冲突）
                await raw_conn.execute(f'DROP TABLE IF EXISTS "{tmp_table}"')

                batch_elapsed = time.monotonic() - batch_start
                processed += len(batch)

                logger.debug(
                    "[COPY] %s: 批次 %d 行, 耗时 %.2fs, %.0f 行/秒",
                    table_name,
                    len(batch),
                    batch_elapsed,
                    len(batch) / batch_elapsed if batch_elapsed > 0 else 0,
                )

            except Exception:
                # 确保临时表被清理
                await raw_conn.execute(
                    f'DROP TABLE IF EXISTS "{tmp_table}"'
                )
                raise

    elapsed = time.monotonic() - start
    rate = processed / elapsed if elapsed > 0 else 0
    logger.info(
        "[COPY] %s: 共 %d 行, 耗时 %.2fs, %.0f 行/秒",
        table_name, processed, elapsed, rate,
    )
    return processed
