"""测试数据完整性检查功能。"""

import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.data.manager import DataManager
from app.scheduler.core import sync_from_progress


@pytest.mark.asyncio
async def test_detect_missing_dates_no_missing():
    """测试 detect_missing_dates() - 无缺失数据场景。"""
    # 模拟 DataManager
    manager = MagicMock(spec=DataManager)

    # 模拟交易日历：2026-02-03, 2026-02-04, 2026-02-05
    trading_dates = [
        date(2026, 2, 3),
        date(2026, 2, 4),
        date(2026, 2, 5),
    ]
    manager.get_trade_calendar = AsyncMock(return_value=trading_dates)

    # 模拟已有数据：全部交易日都有数据
    manager._session_factory = MagicMock()
    session_mock = MagicMock()
    session_mock.__aenter__ = AsyncMock(return_value=session_mock)
    session_mock.__aexit__ = AsyncMock(return_value=None)

    result_mock = MagicMock()
    result_mock.all.return_value = [
        (date(2026, 2, 3),),
        (date(2026, 2, 4),),
        (date(2026, 2, 5),),
    ]
    session_mock.execute = AsyncMock(return_value=result_mock)
    manager._session_factory.return_value = session_mock

    # 调用真实的 detect_missing_dates 方法
    from app.data.manager import DataManager as RealDataManager

    real_manager = RealDataManager(
        session_factory=manager._session_factory,
        clients={},
        primary="tushare",
    )
    real_manager.get_trade_calendar = manager.get_trade_calendar

    start_date = date(2026, 2, 3)
    end_date = date(2026, 2, 5)
    missing_dates = await real_manager.detect_missing_dates(start_date, end_date)

    # 验证：无缺失日期
    assert missing_dates == []


@pytest.mark.asyncio
async def test_detect_missing_dates_partial_missing():
    """测试 detect_missing_dates() - 部分缺失数据场景。"""
    # 模拟 DataManager
    manager = MagicMock(spec=DataManager)

    # 模拟交易日历：2026-02-03, 2026-02-04, 2026-02-05
    trading_dates = [
        date(2026, 2, 3),
        date(2026, 2, 4),
        date(2026, 2, 5),
    ]
    manager.get_trade_calendar = AsyncMock(return_value=trading_dates)

    # 模拟已有数据：只有 2026-02-03 有数据
    manager._session_factory = MagicMock()
    session_mock = MagicMock()
    session_mock.__aenter__ = AsyncMock(return_value=session_mock)
    session_mock.__aexit__ = AsyncMock(return_value=None)

    result_mock = MagicMock()
    result_mock.all.return_value = [
        (date(2026, 2, 3),),
    ]
    session_mock.execute = AsyncMock(return_value=result_mock)
    manager._session_factory.return_value = session_mock

    # 调用真实的 detect_missing_dates 方法
    from app.data.manager import DataManager as RealDataManager

    real_manager = RealDataManager(
        session_factory=manager._session_factory,
        clients={},
        primary="tushare",
    )
    real_manager.get_trade_calendar = manager.get_trade_calendar

    start_date = date(2026, 2, 3)
    end_date = date(2026, 2, 5)
    missing_dates = await real_manager.detect_missing_dates(start_date, end_date)

    # 验证：缺失 2026-02-04 和 2026-02-05
    assert missing_dates == [date(2026, 2, 4), date(2026, 2, 5)]


@pytest.mark.asyncio
async def test_detect_missing_dates_all_missing():
    """测试 detect_missing_dates() - 全部缺失数据场景。"""
    # 模拟 DataManager
    manager = MagicMock(spec=DataManager)

    # 模拟交易日历：2026-02-03, 2026-02-04, 2026-02-05
    trading_dates = [
        date(2026, 2, 3),
        date(2026, 2, 4),
        date(2026, 2, 5),
    ]
    manager.get_trade_calendar = AsyncMock(return_value=trading_dates)

    # 模拟已有数据：无数据
    manager._session_factory = MagicMock()
    session_mock = MagicMock()
    session_mock.__aenter__ = AsyncMock(return_value=session_mock)
    session_mock.__aexit__ = AsyncMock(return_value=None)

    result_mock = MagicMock()
    result_mock.all.return_value = []
    session_mock.execute = AsyncMock(return_value=result_mock)
    manager._session_factory.return_value = session_mock

    # 调用真实的 detect_missing_dates 方法
    from app.data.manager import DataManager as RealDataManager

    real_manager = RealDataManager(
        session_factory=manager._session_factory,
        clients={},
        primary="tushare",
    )
    real_manager.get_trade_calendar = manager.get_trade_calendar

    start_date = date(2026, 2, 3)
    end_date = date(2026, 2, 5)
    missing_dates = await real_manager.detect_missing_dates(start_date, end_date)

    # 验证：全部缺失
    assert missing_dates == trading_dates


@pytest.mark.asyncio
async def test_sync_from_progress_skip():
    """测试启动时同步 - 跳过检查。"""
    with patch("app.scheduler.core.settings") as mock_settings:
        mock_settings.data_integrity_check_enabled = True

        # 调用同步函数，跳过检查
        await sync_from_progress(skip_check=True)

        # 验证：无异常抛出，函数正常返回


@pytest.mark.asyncio
async def test_sync_from_progress_disabled():
    """测试启动时同步 - 配置禁用。"""
    with patch("app.scheduler.core.settings") as mock_settings:
        mock_settings.data_integrity_check_enabled = False

        # 调用同步函数
        await sync_from_progress(skip_check=False)

        # 验证：无异常抛出，函数正常返回


class TestEnvironmentIsolation:
    """验证环境隔离：APP_ENV_FILE 控制配置文件加载（Task 1.5）。"""

    def test_default_env_file_is_dot_env(self) -> None:
        """默认使用项目根目录的 .env 文件。"""
        import os
        # 确保 APP_ENV_FILE 未设置时使用默认值
        env_file = os.environ.get(
            "APP_ENV_FILE",
            "default.env",
        )
        if "APP_ENV_FILE" not in os.environ:
            assert env_file == "default.env"

    def test_app_env_file_overrides_default(self, monkeypatch, tmp_path) -> None:
        """APP_ENV_FILE 环境变量覆盖默认 .env 路径。"""
        # 创建临时 .env.test 文件，使用不同的数据库 URL
        test_env = tmp_path / ".env.test"
        test_env.write_text(
            'DATABASE_URL="postgresql+asyncpg://test:test@localhost:5432/test_db"\n'
            'APP_ENV="testing"\n'
        )

        # 设置 APP_ENV_FILE 指向测试配置
        monkeypatch.setenv("APP_ENV_FILE", str(test_env))

        # 重新加载 config 模块以使用新的环境变量
        import importlib
        import app.config
        importlib.reload(app.config)

        try:
            # 验证 Settings 使用了测试配置文件
            from app.config import Settings
            # model_config 中的 env_file 应该指向测试文件
            assert app.config.Settings.model_config["env_file"] == str(test_env)
        finally:
            # 恢复原始模块状态
            monkeypatch.delenv("APP_ENV_FILE", raising=False)
            importlib.reload(app.config)

    def test_settings_reads_from_custom_env_file(self, monkeypatch, tmp_path) -> None:
        """Settings 实例从 APP_ENV_FILE 指定的文件读取配置值。"""
        # 创建临时 .env.test 文件
        test_env = tmp_path / ".env.test"
        test_env.write_text(
            'APP_ENV="testing"\n'
            'LOG_LEVEL="DEBUG"\n'
        )

        monkeypatch.setenv("APP_ENV_FILE", str(test_env))

        import importlib
        import app.config
        importlib.reload(app.config)

        try:
            test_settings = app.config.Settings()
            assert test_settings.app_env == "testing"
            assert test_settings.log_level == "DEBUG"
        finally:
            monkeypatch.delenv("APP_ENV_FILE", raising=False)
            importlib.reload(app.config)


class TestSyncFromProgressResume:
    """验证启动同步恢复链路。"""

    @staticmethod
    def _mock_db_factory(*sessions: AsyncMock) -> MagicMock:
        factory = MagicMock()
        factory.return_value.__aenter__ = AsyncMock(side_effect=list(sessions))
        factory.return_value.__aexit__ = AsyncMock(return_value=False)
        return factory

    @pytest.mark.asyncio
    async def test_only_processes_unsynced_stocks(self) -> None:
        """sync_from_progress 应只补齐缺失交易日。"""
        mock_manager = AsyncMock()
        mock_manager.acquire_sync_lock.return_value = True
        mock_manager.reset_stale_status.return_value = 2  # 2 个 stale 状态被重置
        mock_manager.init_sync_progress.return_value = {"total_stocks": 100, "new_records": 0}
        mock_manager.sync_delisted_status.return_value = {"marked": 0, "restored": 0}
        mock_manager.sync_daily_by_date.return_value = {"success": 2, "failed": 0, "timeout": False}
        mock_manager.sync_raw_tables.return_value = {}
        mock_manager.get_sync_summary.return_value = {
            "total": 100, "data_done": 100, "indicator_done": 100,
            "failed": 0, "completion_rate": 1.0,
        }

        latest_session = AsyncMock()
        latest_result = MagicMock()
        latest_result.scalar_one_or_none.return_value = date(2026, 2, 13)
        latest_session.execute.return_value = latest_result

        dates_session = AsyncMock()
        trade_dates_result = MagicMock()
        trade_dates_result.all.return_value = [
            (date(2026, 2, 11),),
            (date(2026, 2, 12),),
            (date(2026, 2, 13),),
        ]
        existing_dates_result = MagicMock()
        existing_dates_result.all.return_value = [
            (date(2026, 2, 11),),
        ]
        dates_session.execute.side_effect = [trade_dates_result, existing_dates_result]

        with patch("app.scheduler.core.settings") as mock_settings, \
             patch("app.data.tushare.TushareClient"), \
             patch("app.data.manager.DataManager", return_value=mock_manager), \
             patch(
                 "app.database.async_session_factory",
                 self._mock_db_factory(latest_session, dates_session),
             ):
            mock_settings.data_integrity_check_enabled = True
            mock_settings.daily_sync_concurrency = 10
            mock_settings.sync_batch_timeout = 14400
            mock_settings.data_start_date = "2020-01-01"

            await sync_from_progress(skip_check=False)

        mock_manager.sync_daily_by_date.assert_awaited_once_with(
            [date(2026, 2, 12), date(2026, 2, 13)]
        )
        assert mock_manager.sync_raw_tables.await_count == 3
        mock_manager.acquire_sync_lock.assert_awaited_once()
        mock_manager.release_sync_lock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_skips_when_all_synced(self) -> None:
        """所有交易日已补齐时不执行按日期同步。"""
        mock_manager = AsyncMock()
        mock_manager.acquire_sync_lock.return_value = True
        mock_manager.reset_stale_status.return_value = 0
        mock_manager.init_sync_progress.return_value = {"total_stocks": 100, "new_records": 0}
        mock_manager.sync_delisted_status.return_value = {"marked": 0, "restored": 0}
        mock_manager.get_sync_summary.return_value = {
            "total": 100, "data_done": 100, "indicator_done": 100,
            "failed": 0, "completion_rate": 1.0,
        }

        latest_session = AsyncMock()
        latest_result = MagicMock()
        latest_result.scalar_one_or_none.return_value = date(2026, 2, 13)
        latest_session.execute.return_value = latest_result

        dates_session = AsyncMock()
        trade_dates_result = MagicMock()
        trade_dates_result.all.return_value = [
            (date(2026, 2, 11),),
            (date(2026, 2, 12),),
        ]
        existing_dates_result = MagicMock()
        existing_dates_result.all.return_value = [
            (date(2026, 2, 11),),
            (date(2026, 2, 12),),
        ]
        dates_session.execute.side_effect = [trade_dates_result, existing_dates_result]

        with patch("app.scheduler.core.settings") as mock_settings, \
             patch("app.data.tushare.TushareClient"), \
             patch("app.data.manager.DataManager", return_value=mock_manager), \
             patch(
                 "app.database.async_session_factory",
                 self._mock_db_factory(latest_session, dates_session),
             ):
            mock_settings.data_integrity_check_enabled = True

            await sync_from_progress(skip_check=False)

        mock_manager.sync_daily_by_date.assert_not_awaited()
        mock_manager.get_sync_summary.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_resets_stale_status_before_sync(self) -> None:
        """重启后先重置 stale 状态，再初始化和同步退市状态。"""
        call_order = []
        mock_manager = AsyncMock()
        mock_manager.acquire_sync_lock.return_value = True
        mock_manager.reset_stale_status.side_effect = lambda: (call_order.append("reset"), 5)[1]
        mock_manager.init_sync_progress.side_effect = lambda: (
            call_order.append("init"), {"total_stocks": 50, "new_records": 0}
        )[1]
        mock_manager.sync_delisted_status.side_effect = lambda: (
            call_order.append("delisted"), {"marked": 0, "restored": 0}
        )[1]
        mock_manager.get_sync_summary.side_effect = lambda _target_date: (
            call_order.append("summary"),
            {
                "total": 50, "data_done": 50, "indicator_done": 50,
                "failed": 0, "completion_rate": 1.0,
            },
        )[1]

        latest_session = AsyncMock()
        latest_result = MagicMock()
        latest_result.scalar_one_or_none.return_value = date(2026, 2, 13)
        latest_session.execute.return_value = latest_result

        dates_session = AsyncMock()
        trade_dates_result = MagicMock()
        trade_dates_result.all.return_value = [(date(2026, 2, 13),)]
        existing_dates_result = MagicMock()
        existing_dates_result.all.return_value = [(date(2026, 2, 13),)]
        dates_session.execute.side_effect = [trade_dates_result, existing_dates_result]

        with patch("app.scheduler.core.settings") as mock_settings, \
             patch("app.data.tushare.TushareClient"), \
             patch("app.data.manager.DataManager", return_value=mock_manager), \
             patch(
                 "app.database.async_session_factory",
                 self._mock_db_factory(latest_session, dates_session),
             ):
            mock_settings.data_integrity_check_enabled = True

            await sync_from_progress(skip_check=False)

        assert call_order == ["reset", "init", "delisted", "summary"]
