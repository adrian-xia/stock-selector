"""测试回测数据加载模块 data_feed。

覆盖场景：
1. load_stock_data 正常加载并验证前复权公式
2. load_stock_data 无数据返回空 DataFrame
3. build_data_feed 字段映射正确
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest

from app.backtest.data_feed import PandasDataPlus, build_data_feed, load_stock_data


# ---------------------------------------------------------------------------
# load_stock_data 测试
# ---------------------------------------------------------------------------


class TestLoadStockData:
    """测试 load_stock_data 数据库加载与前复权逻辑。"""

    async def test_normal_load_with_forward_adjust(self) -> None:
        """正常加载：验证前复权公式 price_adj = price_raw * (adj_factor / latest_adj_factor)。"""
        # 构造 3 天的模拟数据库返回行
        # 第 1 天 adj_factor=10，第 2 天 adj_factor=12，第 3 天（最新）adj_factor=15
        # latest_adj_factor = 15
        # 第 1 天 adj_ratio = 10/15 ≈ 0.6667
        # 第 2 天 adj_ratio = 12/15 = 0.8
        # 第 3 天 adj_ratio = 15/15 = 1.0
        mock_rows = [
            # (trade_date, open, high, low, close, vol, amount, turnover_rate, adj_factor)
            (date(2024, 1, 2), 30.0, 33.0, 29.0, 31.5, 1000000, 31500000, 2.5, 10.0),
            (date(2024, 1, 3), 31.5, 34.0, 30.0, 33.0, 1200000, 39600000, 3.0, 12.0),
            (date(2024, 1, 4), 33.0, 35.0, 32.0, 34.0, 800000, 27200000, 1.8, 15.0),
        ]

        # 构造 mock AsyncSession
        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        df = await load_stock_data(
            session=mock_session,
            ts_code="600519.SH",
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 4),
        )

        # 基本结构验证
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert df.index.name == "trade_date"

        # 验证列存在
        for col in ["open", "high", "low", "close", "vol", "amount", "turnover_rate", "adj_factor"]:
            assert col in df.columns

        # 验证前复权计算
        latest_adj = 15.0

        # 第 1 天：adj_ratio = 10/15
        adj_ratio_day1 = 10.0 / latest_adj
        assert df["open"].iloc[0] == pytest.approx(30.0 * adj_ratio_day1, rel=1e-6)
        assert df["high"].iloc[0] == pytest.approx(33.0 * adj_ratio_day1, rel=1e-6)
        assert df["low"].iloc[0] == pytest.approx(29.0 * adj_ratio_day1, rel=1e-6)
        assert df["close"].iloc[0] == pytest.approx(31.5 * adj_ratio_day1, rel=1e-6)

        # 第 2 天：adj_ratio = 12/15 = 0.8
        adj_ratio_day2 = 12.0 / latest_adj
        assert df["open"].iloc[1] == pytest.approx(31.5 * adj_ratio_day2, rel=1e-6)
        assert df["close"].iloc[1] == pytest.approx(33.0 * adj_ratio_day2, rel=1e-6)

        # 第 3 天（最新）：adj_ratio = 15/15 = 1.0，价格不变
        assert df["open"].iloc[2] == pytest.approx(33.0, rel=1e-6)
        assert df["close"].iloc[2] == pytest.approx(34.0, rel=1e-6)

        # vol、amount、turnover_rate 不受前复权影响
        assert df["vol"].iloc[0] == pytest.approx(1000000)
        assert df["amount"].iloc[1] == pytest.approx(39600000)
        assert df["turnover_rate"].iloc[2] == pytest.approx(1.8)

    async def test_empty_result_returns_empty_dataframe(self) -> None:
        """数据库无数据时返回空 DataFrame。"""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        df = await load_stock_data(
            session=mock_session,
            ts_code="000001.SZ",
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 30),
        )

        assert isinstance(df, pd.DataFrame)
        assert df.empty

    async def test_sql_params_passed_correctly(self) -> None:
        """验证 SQL 参数正确传递给 session.execute。"""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        await load_stock_data(
            session=mock_session,
            ts_code="600519.SH",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

        # 验证 execute 被调用一次
        mock_session.execute.assert_awaited_once()
        call_args = mock_session.execute.call_args
        params = call_args[0][1]  # 第二个位置参数是参数字典
        assert params["ts_code"] == "600519.SH"
        assert params["start_date"] == date(2024, 1, 1)
        assert params["end_date"] == date(2024, 12, 31)

    async def test_datetime_index_is_set(self) -> None:
        """验证返回的 DataFrame 以 trade_date 为 DatetimeIndex。"""
        mock_rows = [
            (date(2024, 3, 1), 10.0, 11.0, 9.5, 10.5, 500000, 5250000, 1.0, 1.0),
        ]

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        df = await load_stock_data(
            session=mock_session,
            ts_code="000002.SZ",
            start_date=date(2024, 3, 1),
            end_date=date(2024, 3, 1),
        )

        assert isinstance(df.index, pd.DatetimeIndex)
        assert df.index.name == "trade_date"

    async def test_uniform_adj_factor_no_change(self) -> None:
        """所有交易日 adj_factor 相同时，价格不变（adj_ratio 全为 1.0）。"""
        mock_rows = [
            (date(2024, 5, 6), 20.0, 21.0, 19.0, 20.5, 600000, 12300000, 2.0, 1.0),
            (date(2024, 5, 7), 20.5, 22.0, 20.0, 21.0, 700000, 14700000, 2.2, 1.0),
        ]

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        df = await load_stock_data(
            session=mock_session,
            ts_code="600036.SH",
            start_date=date(2024, 5, 6),
            end_date=date(2024, 5, 7),
        )

        # adj_factor 全为 1.0，latest_adj = 1.0，adj_ratio = 1.0，价格不变
        assert df["open"].iloc[0] == pytest.approx(20.0, rel=1e-6)
        assert df["close"].iloc[0] == pytest.approx(20.5, rel=1e-6)
        assert df["open"].iloc[1] == pytest.approx(20.5, rel=1e-6)
        assert df["close"].iloc[1] == pytest.approx(21.0, rel=1e-6)


# ---------------------------------------------------------------------------
# build_data_feed 测试
# ---------------------------------------------------------------------------


class TestBuildDataFeed:
    """测试 build_data_feed 将 DataFrame 转换为 Backtrader DataFeed。"""

    @staticmethod
    def _make_df(days: int = 5) -> pd.DataFrame:
        """构造测试用 DataFrame（模拟 load_stock_data 的输出格式）。"""
        dates = pd.bdate_range(start="2024-01-02", periods=days)
        return pd.DataFrame(
            {
                "open": [10.0 + i for i in range(days)],
                "high": [10.5 + i for i in range(days)],
                "low": [9.5 + i for i in range(days)],
                "close": [10.2 + i for i in range(days)],
                "vol": [1000000] * days,
                "amount": [10000000] * days,
                "turnover_rate": [1.5 + i * 0.1 for i in range(days)],
                "adj_factor": [1.0] * days,
            },
            index=dates,
        )

    def test_returns_pandas_data_plus(self) -> None:
        """返回类型为 PandasDataPlus。"""
        df = self._make_df()
        feed = build_data_feed(df, name="600519.SH")
        assert isinstance(feed, PandasDataPlus)

    def test_name_is_set(self) -> None:
        """验证 DataFeed 的 name 参数正确设置。"""
        df = self._make_df()
        feed = build_data_feed(df, name="000001.SZ")
        # PandasData 的 _name 属性存储 name
        assert feed.params.name == "000001.SZ"  # type: ignore[attr-defined]

    def test_turnover_rate_mapped(self) -> None:
        """验证 turnover_rate 字段映射到自定义 line。"""
        df = self._make_df()
        feed = build_data_feed(df, name="600519.SH")
        # 参数应指向 DataFrame 列名
        assert feed.params.turnover_rate == "turnover_rate"  # type: ignore[attr-defined]

    def test_adj_factor_mapped(self) -> None:
        """验证 adj_factor 字段映射到自定义 line。"""
        df = self._make_df()
        feed = build_data_feed(df, name="600519.SH")
        assert feed.params.adj_factor == "adj_factor"  # type: ignore[attr-defined]

    def test_volume_mapped_to_vol(self) -> None:
        """验证 volume 映射到 DataFrame 的 vol 列。"""
        df = self._make_df()
        feed = build_data_feed(df, name="600519.SH")
        # PandasDataPlus 的 params 中 volume 映射到 "vol"
        assert feed.params.volume == "vol"  # type: ignore[attr-defined]

    def test_dataname_is_dataframe(self) -> None:
        """验证 dataname 参数指向传入的 DataFrame。"""
        df = self._make_df()
        feed = build_data_feed(df, name="600519.SH")
        assert feed.params.dataname is df  # type: ignore[attr-defined]

    def test_custom_lines_declared(self) -> None:
        """验证 PandasDataPlus 声明了 turnover_rate 和 adj_factor 两条自定义 line。"""
        assert "turnover_rate" in PandasDataPlus.lines._getlines()
        assert "adj_factor" in PandasDataPlus.lines._getlines()
