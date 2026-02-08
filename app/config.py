from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Application ---
    app_name: str = "stock-selector"
    app_env: str = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"

    # --- Database ---
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/stock_selector"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_echo: bool = False

    # --- Redis ---
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""

    # --- BaoStock ---
    baostock_retry_count: int = 3
    baostock_retry_interval: float = 2.0
    baostock_timeout: int = 30
    baostock_qps_limit: int = 5

    # --- AKShare ---
    akshare_retry_count: int = 3
    akshare_retry_interval: float = 1.0
    akshare_timeout: int = 20
    akshare_qps_limit: int = 10

    # --- ETL ---
    etl_batch_size: int = 5000
    etl_commit_interval: int = 10

    # --- Scheduler ---
    scheduler_post_market_cron: str = "30 15 * * 1-5"  # 周一至周五 15:30
    scheduler_stock_sync_cron: str = "0 8 * * 6"       # 周六 08:00


settings = Settings()
