"""测试启动期策略同步与清理。"""

from unittest.mock import AsyncMock

import pytest

from app.main import _build_active_strategy_rows, _cleanup_obsolete_strategy_data


class _Result:
    def __init__(self, rows=None, rowcount: int | None = None) -> None:
        self._rows = rows or []
        self.rowcount = rowcount

    def fetchall(self):
        return self._rows


def test_build_active_strategy_rows_contains_v2_and_v4() -> None:
    rows = _build_active_strategy_rows()
    names = {row["name"] for row in rows}

    assert "volume-breakout-trigger-v2" in names
    assert "volume-price-pattern" in names
    assert "ma-cross" not in names


@pytest.mark.asyncio
async def test_cleanup_obsolete_strategy_data_deletes_related_rows() -> None:
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[
        _Result(rows=[(1, "ma-cross"), (2, "pb-value")]),
        _Result(rowcount=5),
        _Result(rowcount=2),
        _Result(rowcount=1),
        _Result(rowcount=8),
        _Result(rowcount=7),
        _Result(rowcount=3),
        _Result(rowcount=0),
        _Result(rowcount=4),
        _Result(rowcount=4),
        _Result(rowcount=2),
    ])

    stats = await _cleanup_obsolete_strategy_data(
        session,
        ["volume-breakout-trigger-v2", "volume-price-pattern"],
    )

    assert stats["strategies"] == 2
    assert stats["optimization_results"] == 5
    assert stats["backtest_tasks"] == 4

    sql_texts = [str(call.args[0]) for call in session.execute.call_args_list]
    assert any("DELETE FROM strategies" in sql for sql in sql_texts)
    assert any("DELETE FROM strategy_picks" in sql for sql in sql_texts)
