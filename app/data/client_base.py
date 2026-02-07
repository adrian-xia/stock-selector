from datetime import date
from typing import Protocol, runtime_checkable


@runtime_checkable
class DataSourceClient(Protocol):
    """Protocol defining the interface for all data source clients."""

    async def fetch_daily(
        self, code: str, start_date: date, end_date: date
    ) -> list[dict]:
        """Fetch daily OHLCV bar data for a single stock."""
        ...

    async def fetch_stock_list(self) -> list[dict]:
        """Fetch the complete A-share stock list."""
        ...

    async def fetch_trade_calendar(
        self, start_date: date, end_date: date
    ) -> list[dict]:
        """Fetch trade calendar data."""
        ...

    async def health_check(self) -> bool:
        """Check if the data source is reachable."""
        ...
