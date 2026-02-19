"""DataManager.get_latest_technical() 查询接口的单元测试。

使用 mock 替代数据库会话，测试查询逻辑和字段选择功能。
"""

from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest

from app.data.manager import DataManager


class _FakeAsyncSession:
    """模拟 AsyncSession 的 async context manager。"""

    def __init__(self, execute_return):
        self._execute_return = execute_return

    async def execute(self, stmt):
        mock_result = MagicMock()
        mock_result.all.return_value = self._execute_return
        return mock_result

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class _FakeSessionFactory:
    """模拟 async_sessionmaker，调用后返回 async context manager。"""

    def __init__(self, execute_return):
        self._execute_return = execute_return

    def __call__(self):
        return _FakeAsyncSession(self._execute_return)


def _make_manager_with_mock(execute_return=None) -> DataManager:
    """构造一个带 mock session_factory 的 DataManager 实例。"""
    if execute_return is None:
        execute_return = []
    mock_clients = {"tushare": MagicMock()}
    return DataManager(
        session_factory=_FakeSessionFactory(execute_return),
        clients=mock_clients,
        primary="tushare",
    )


class TestGetLatestTechnical:
    """测试 get_latest_technical() 方法。"""

    @pytest.mark.asyncio
    async def test_empty_result_returns_correct_schema(self):
        """验证无数据时返回空 DataFrame 且列结构正确。"""
        manager = _make_manager_with_mock([])

        result = await manager.get_latest_technical(["999999.SH"])

        assert isinstance(result, pd.DataFrame)
        assert result.empty
        assert "ts_code" in result.columns
        assert "trade_date" in result.columns
        assert "ma5" in result.columns
        assert "atr14" in result.columns

    @pytest.mark.asyncio
    async def test_empty_result_with_fields_selection(self):
        """验证指定 fields 时空结果的列结构正确。"""
        manager = _make_manager_with_mock([])

        result = await manager.get_latest_technical(
            ["600519.SH"],
            fields=["ma5", "ma10", "rsi6"],
        )

        assert isinstance(result, pd.DataFrame)
        assert result.empty
        assert "ts_code" in result.columns
        assert "trade_date" in result.columns
        assert "ma5" in result.columns
        assert "ma10" in result.columns
        assert "rsi6" in result.columns
        # 不应包含未请求的列
        assert "ma250" not in result.columns
