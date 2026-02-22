"""TimescaleDB 超表迁移 + 压缩策略

stock_daily 和 technical_daily 转为 TimescaleDB 超表，
配置自动压缩策略。TimescaleDB 不可用时安全跳过。

Revision ID: d1a2b3c4e5f6
Revises: c3f5e7a19b60
Create Date: 2026-02-22
"""

from alembic import op
import sqlalchemy as sa

revision = "d1a2b3c4e5f6"
down_revision = "c3f5e7a19b60"
branch_labels = None
depends_on = None

# 需要转为超表的表
HYPERTABLES = [
    {
        "table": "stock_daily",
        "time_column": "trade_date",
        "segment_by": "ts_code",
    },
    {
        "table": "technical_daily",
        "time_column": "trade_date",
        "segment_by": "ts_code",
    },
]

# 压缩阈值（天），从配置读取或使用默认值
COMPRESS_AFTER_DAYS = 30


def _is_timescaledb_available(connection) -> bool:
    """检测 TimescaleDB 扩展是否可用。"""
    result = connection.execute(
        sa.text("SELECT 1 FROM pg_available_extensions WHERE name = 'timescaledb'")
    )
    return result.fetchone() is not None


def upgrade() -> None:
    connection = op.get_bind()

    if not _is_timescaledb_available(connection):
        print("WARNING: TimescaleDB 不可用，跳过超表迁移。表保持为普通表。")
        return

    # 1. 启用 TimescaleDB 扩展
    connection.execute(sa.text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
    print("INFO: TimescaleDB 扩展已启用")

    # 2. 转换为超表 + 配置压缩
    for ht in HYPERTABLES:
        table = ht["table"]
        time_col = ht["time_column"]
        segment_by = ht["segment_by"]

        # 检查是否已经是超表
        result = connection.execute(sa.text(
            "SELECT 1 FROM timescaledb_information.hypertables "
            "WHERE hypertable_name = :table_name"
        ), {"table_name": table})

        if result.fetchone():
            print(f"INFO: {table} 已经是超表，跳过转换")
            continue

        # 转换为超表（migrate_data=true 迁移已有数据）
        connection.execute(sa.text(
            f"SELECT create_hypertable('{table}', '{time_col}', "
            f"chunk_time_interval => interval '1 month', "
            f"migrate_data => true)"
        ))
        print(f"INFO: {table} 已转换为超表（按月分区）")

        # 启用压缩
        connection.execute(sa.text(
            f"ALTER TABLE {table} SET ("
            f"timescaledb.compress, "
            f"timescaledb.compress_segmentby = '{segment_by}', "
            f"timescaledb.compress_orderby = '{time_col} DESC')"
        ))

        # 添加压缩策略
        connection.execute(sa.text(
            f"SELECT add_compression_policy('{table}', "
            f"interval '{COMPRESS_AFTER_DAYS} days')"
        ))
        print(f"INFO: {table} 压缩策略已配置（{COMPRESS_AFTER_DAYS} 天后自动压缩）")


def downgrade() -> None:
    connection = op.get_bind()

    if not _is_timescaledb_available(connection):
        print("WARNING: TimescaleDB 不可用，无需回滚")
        return

    # 超表转换不可自动回滚，记录警告
    print("WARNING: TimescaleDB 超表转换不可自动回滚。")
    print("如需回滚，请手动执行以下步骤：")
    for ht in HYPERTABLES:
        table = ht["table"]
        print(f"  1. pg_dump -t {table} > {table}_backup.sql")
        print(f"  2. DROP TABLE {table};")
        print(f"  3. 重建普通表并导入数据")

    # 移除压缩策略（可安全执行）
    for ht in HYPERTABLES:
        table = ht["table"]
        try:
            connection.execute(sa.text(
                f"SELECT remove_compression_policy('{table}', if_exists => true)"
            ))
            print(f"INFO: {table} 压缩策略已移除")
        except Exception as e:
            print(f"WARNING: 移除 {table} 压缩策略失败: {e}")
