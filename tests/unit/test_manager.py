import pandas as pd

from app.data.manager import DataManager


class TestApplyAdjustment:
    def test_forward_adjustment(self):
        df = pd.DataFrame({
            "ts_code": ["600519.SH", "600519.SH", "600519.SH"],
            "trade_date": ["2025-01-01", "2025-01-02", "2025-01-03"],
            "open": [100.0, 105.0, 110.0],
            "high": [102.0, 107.0, 112.0],
            "low": [98.0, 103.0, 108.0],
            "close": [101.0, 106.0, 111.0],
            "adj_factor": [1.0, 1.0, 2.0],
        })
        result = DataManager._apply_adjustment(df.copy(), "qfq")
        # Latest factor is 2.0
        # Day 1: close = 101 * 1.0 / 2.0 = 50.5
        # Day 3: close = 111 * 2.0 / 2.0 = 111.0
        assert abs(result.iloc[0]["close"] - 50.5) < 0.01
        assert abs(result.iloc[2]["close"] - 111.0) < 0.01
        assert "adj_factor" not in result.columns

    def test_backward_adjustment(self):
        df = pd.DataFrame({
            "ts_code": ["600519.SH"],
            "trade_date": ["2025-01-01"],
            "open": [100.0],
            "high": [102.0],
            "low": [98.0],
            "close": [101.0],
            "adj_factor": [1.5],
        })
        result = DataManager._apply_adjustment(df.copy(), "hfq")
        # hfq: close = 101 * 1.5 = 151.5
        assert abs(result.iloc[0]["close"] - 151.5) < 0.01

    def test_no_adj_factor(self):
        df = pd.DataFrame({
            "ts_code": ["600519.SH"],
            "trade_date": ["2025-01-01"],
            "open": [100.0],
            "high": [102.0],
            "low": [98.0],
            "close": [101.0],
            "adj_factor": [None],
        })
        result = DataManager._apply_adjustment(df.copy(), "qfq")
        # No adjustment when all factors are NaN
        assert abs(result.iloc[0]["close"] - 101.0) < 0.01

    def test_empty_dataframe(self):
        df = pd.DataFrame(columns=["ts_code", "open", "close", "adj_factor"])
        result = DataManager._apply_adjustment(df, "qfq")
        assert result.empty
