"""index_mgmt 模块单元测试。

测试索引管理的核心逻辑：
- drop_indexes 查询和删除非主键索引
- rebuild_indexes 使用 CONCURRENTLY 重建
- with_index_management 上下文管理器
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.data.index_mgmt import (
    IndexDefinition,
    drop_indexes,
    rebuild_indexes,
    with_index_management,
)


def _make_mock_engine(index_rows=None):
    """创建模拟的 async engine。"""
    engine = MagicMock()
    conn = AsyncMock()

    if index_rows is None:
        index_rows = []

    result = MagicMock()
    result.fetchall.return_value = index_rows
    conn.execute = AsyncMock(return_value=result)
    conn.execution_options = AsyncMock(return_value=None)

    @asynccontextmanager
    async def _begin():
        yield conn

    @asynccontextmanager
    async def _connect():
        yield conn

    engine.begin = _begin
    engine.connect = _connect

    return engine, conn


class TestDropIndexes:
    """drop_indexes 测试。"""

    @pytest.mark.asyncio
    async def test_no_indexes(self):
        """无非主键索引时返回空列表。"""
        engine, _ = _make_mock_engine(index_rows=[])
        result = await drop_indexes(engine, "stock_daily")
        assert result == []

    @pytest.mark.asyncio
    async def test_drop_indexes(self):
        """应删除非主键索引并返回定义。"""
        index_rows = [
            ("idx_stock_daily_trade_date", "CREATE INDEX idx_stock_daily_trade_date ON stock_daily (trade_date)"),
            ("idx_stock_daily_code_date", "CREATE INDEX idx_stock_daily_code_date ON stock_daily (ts_code, trade_date DESC)"),
        ]
        engine, conn = _make_mock_engine(index_rows=index_rows)
        result = await drop_indexes(engine, "stock_daily")

        assert len(result) == 2
        assert result[0].name == "idx_stock_daily_trade_date"
        assert result[1].name == "idx_stock_daily_code_date"
        # 应执行 1 次查询 + 2 次 DROP
        assert conn.execute.call_count == 3


class TestRebuildIndexes:
    """rebuild_indexes 测试。"""

    @pytest.mark.asyncio
    async def test_rebuild_success(self):
        """成功重建索引。"""
        engine, conn = _make_mock_engine()
        conn.execution_options = AsyncMock(return_value=None)

        index_defs = [
            IndexDefinition(
                name="idx_test",
                table_name="test_table",
                definition="CREATE INDEX idx_test ON test_table (col1)",
            ),
        ]
        failed = await rebuild_indexes(engine, index_defs)
        assert failed == []

    @pytest.mark.asyncio
    async def test_rebuild_failure_continues(self):
        """单个索引重建失败不影响其他索引。"""
        engine = MagicMock()

        call_count = 0

        @asynccontextmanager
        async def mock_connect():
            nonlocal call_count
            conn = AsyncMock()
            conn.execution_options = AsyncMock(return_value=None)
            if call_count == 0:
                conn.execute = AsyncMock(side_effect=Exception("rebuild error"))
            call_count += 1
            yield conn

        engine.connect = mock_connect

        index_defs = [
            IndexDefinition("idx_fail", "t1", "CREATE INDEX idx_fail ON t1 (c1)"),
            IndexDefinition("idx_ok", "t1", "CREATE INDEX idx_ok ON t1 (c2)"),
        ]
        failed = await rebuild_indexes(engine, index_defs)
        assert "idx_fail" in failed
        assert len(failed) == 1


class TestWithIndexManagement:
    """with_index_management 上下文管理器测试。"""

    @pytest.mark.asyncio
    async def test_context_manager_normal(self):
        """正常流程：删除 → 执行 → 重建。"""
        with patch("app.data.index_mgmt.drop_indexes") as mock_drop, \
             patch("app.data.index_mgmt.rebuild_indexes") as mock_rebuild:
            mock_drop.return_value = [
                IndexDefinition("idx_1", "t1", "CREATE INDEX idx_1 ON t1 (c1)"),
            ]
            mock_rebuild.return_value = []

            engine = AsyncMock()
            async with with_index_management(engine, ["t1"]) as indexes:
                assert len(indexes) == 1

            mock_drop.assert_called_once()
            mock_rebuild.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_exception_still_rebuilds(self):
        """异常时仍然重建索引。"""
        with patch("app.data.index_mgmt.drop_indexes") as mock_drop, \
             patch("app.data.index_mgmt.rebuild_indexes") as mock_rebuild:
            mock_drop.return_value = [
                IndexDefinition("idx_1", "t1", "CREATE INDEX idx_1 ON t1 (c1)"),
            ]
            mock_rebuild.return_value = []

            engine = AsyncMock()
            with pytest.raises(ValueError, match="test error"):
                async with with_index_management(engine, ["t1"]):
                    raise ValueError("test error")

            # 即使异常，rebuild 仍被调用
            mock_rebuild.assert_called_once()
