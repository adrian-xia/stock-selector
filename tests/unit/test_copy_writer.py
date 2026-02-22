"""copy_writer 模块单元测试。

测试 COPY 协议写入的核心逻辑：
- copy_insert 函数的参数处理
- 大批量自动分批
- 空数据处理
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.data.copy_writer import COPY_BATCH_SIZE, copy_insert


def _make_mock_table(name: str, columns: list[str], pk_cols: list[str]):
    """创建模拟的 SQLAlchemy Table 对象。"""
    table = MagicMock()
    table.name = name

    # 模拟列
    mock_columns = []
    for col_name in columns:
        col = MagicMock()
        col.name = col_name
        mock_columns.append(col)
    table.columns = mock_columns

    # 模拟主键
    pk_mock_columns = []
    for col_name in pk_cols:
        col = MagicMock()
        col.name = col_name
        pk_mock_columns.append(col)
    table.primary_key.columns = pk_mock_columns

    return table


class TestCopyInsertEmptyRows:
    """空数据测试。"""

    @pytest.mark.asyncio
    async def test_empty_rows_returns_zero(self):
        """空行列表应直接返回 0。"""
        table = _make_mock_table("test_table", ["id", "value"], ["id"])
        result = await copy_insert(table, [])
        assert result == 0

    @pytest.mark.asyncio
    async def test_none_like_empty(self):
        """空列表不触发数据库操作。"""
        table = _make_mock_table("test_table", ["id", "value"], ["id"])
        with patch("app.data.copy_writer.get_raw_connection") as mock_conn:
            result = await copy_insert(table, [])
            assert result == 0
            mock_conn.assert_not_called()


class TestCopyInsertBatching:
    """分批逻辑测试。"""

    def test_batch_size_constant(self):
        """默认批量大小为 50000。"""
        assert COPY_BATCH_SIZE == 50000

    @pytest.mark.asyncio
    async def test_single_batch(self):
        """少于 batch_size 的数据应在单批次内完成。"""
        table = _make_mock_table("stock_daily", ["ts_code", "trade_date", "close"], ["ts_code", "trade_date"])
        rows = [{"ts_code": f"00000{i}.SZ", "trade_date": "2026-01-01", "close": 10.0} for i in range(5)]

        mock_raw_conn = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_raw_conn)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("app.data.copy_writer.get_raw_connection", return_value=mock_ctx):
            result = await copy_insert(table, rows, conflict="nothing")

        assert result == 5
        # 应该调用一次 copy_records_to_table
        mock_raw_conn.copy_records_to_table.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_batches(self):
        """超过 batch_size 的数据应分多批次。"""
        table = _make_mock_table("raw_test", ["id", "val"], ["id"])
        rows = [{"id": i, "val": f"v{i}"} for i in range(10)]

        mock_raw_conn = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_raw_conn)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("app.data.copy_writer.get_raw_connection", return_value=mock_ctx):
            # 使用小 batch_size 强制分批
            result = await copy_insert(table, rows, batch_size=3)

        assert result == 10
        # 10 行 / 3 = 4 批次
        assert mock_raw_conn.copy_records_to_table.call_count == 4


class TestCopyInsertConflictModes:
    """冲突处理模式测试。"""

    @pytest.mark.asyncio
    async def test_conflict_nothing_sql(self):
        """conflict='nothing' 应生成 ON CONFLICT DO NOTHING。"""
        table = _make_mock_table("stock_daily", ["ts_code", "trade_date", "close"], ["ts_code", "trade_date"])
        rows = [{"ts_code": "600519.SH", "trade_date": "2026-01-01", "close": 1700.0}]

        mock_raw_conn = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_raw_conn)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("app.data.copy_writer.get_raw_connection", return_value=mock_ctx):
            await copy_insert(table, rows, conflict="nothing")

        # 检查执行的 SQL 包含 DO NOTHING
        calls = mock_raw_conn.execute.call_args_list
        insert_sql = [c for c in calls if "INSERT INTO" in str(c)]
        assert len(insert_sql) > 0
        assert "DO NOTHING" in str(insert_sql[0])

    @pytest.mark.asyncio
    async def test_conflict_update_sql(self):
        """conflict='update' 应生成 ON CONFLICT DO UPDATE。"""
        table = _make_mock_table("raw_tushare_daily", ["ts_code", "trade_date", "close"], ["ts_code", "trade_date"])
        rows = [{"ts_code": "600519.SH", "trade_date": "2026-01-01", "close": 1700.0}]

        mock_raw_conn = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_raw_conn)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("app.data.copy_writer.get_raw_connection", return_value=mock_ctx):
            await copy_insert(table, rows, conflict="update")

        calls = mock_raw_conn.execute.call_args_list
        insert_sql = [c for c in calls if "INSERT INTO" in str(c)]
        assert len(insert_sql) > 0
        assert "DO UPDATE SET" in str(insert_sql[0])
