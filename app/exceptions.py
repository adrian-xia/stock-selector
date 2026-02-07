class DataSourceError(Exception):
    """Raised when a data source API call fails after all retries."""


class DataSyncError(Exception):
    """Raised when data synchronization fails across all sources."""


class InvalidCodeError(ValueError):
    """Raised when a stock code has an invalid format."""
