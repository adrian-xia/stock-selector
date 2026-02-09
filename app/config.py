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
    performance_log_level: str = "INFO"  # 性能日志级别：DEBUG/INFO/WARNING
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
    baostock_pool_size: int = 5                 # 连接池大小（最大并发连接数）
    baostock_pool_timeout: float = 30.0         # 获取连接的超时时间（秒）
    baostock_session_ttl: float = 3600.0        # 会话生存时间（秒）

    # --- AKShare ---
    akshare_retry_count: int = 3
    akshare_retry_interval: float = 1.0
    akshare_timeout: int = 20
    akshare_qps_limit: int = 10

    # --- ETL ---
    etl_batch_size: int = 5000
    etl_commit_interval: int = 10

    # --- Daily Sync ---
    daily_sync_batch_size: int = 100        # 批量同步每批股票数
    daily_sync_concurrency: int = 10        # 批量同步并发数

    # --- Data Integrity Check ---
    data_integrity_check_enabled: bool = True   # 启动时是否检查数据完整性
    data_integrity_check_days: int = 30         # 检查最近 N 天的数据完整性

    # --- Scheduler ---
    scheduler_post_market_cron: str = "30 15 * * 1-5"  # 周一至周五 15:30
    scheduler_stock_sync_cron: str = "0 8 * * 6"       # 周六 08:00

    # --- Auto Data Update (自动数据更新) ---
    auto_update_enabled: bool = True                    # 是否启用自动数据更新
    auto_update_probe_interval: int = 15                # 嗅探间隔（分钟）
    auto_update_probe_timeout: str = "18:00"            # 嗅探超时时间
    auto_update_probe_stocks: list[str] = [             # 嗅探样本股票
        "600519.SH",  # 贵州茅台
        "000001.SZ",  # 平安银行
        "600036.SH",  # 招商银行
        "000858.SZ",  # 五粮液
        "601318.SH",  # 中国平安
    ]
    auto_update_probe_threshold: float = 0.8            # 嗅探成功阈值（80%样本有数据）
    scheduler_auto_update_cron: str = "30 15 * * 1-5"  # 自动更新任务触发时间（周一至周五 15:30）

    # --- AI (Gemini) ---
    gemini_api_key: str = ""                    # 为空则 AI 分析不启用
    gemini_use_adc: bool = False                # 使用 Google ADC 认证（与 API Key 二选一）
    gemini_gcp_project: str = ""                # GCP 项目 ID（ADC 模式必填）
    gemini_gcp_location: str = "us-central1"    # GCP 区域（ADC 模式）
    gemini_model_id: str = "gemini-2.0-flash"   # V1 固定用 Flash
    gemini_max_tokens: int = 4000               # 单次请求最大输出 token
    gemini_timeout: int = 30                    # 请求超时（秒）
    gemini_max_retries: int = 2                 # 瞬态错误重试次数
    ai_daily_budget_usd: float = 1.0            # 每日预算上限（V1 仅日志告警）

    # --- Cache (Redis) ---
    cache_tech_ttl: int = 90000                 # 技术指标缓存 TTL（秒），默认 25 小时
    cache_pipeline_result_ttl: int = 172800     # 选股结果缓存 TTL（秒），默认 48 小时
    cache_warmup_on_startup: bool = True        # 应用启动时是否执行缓存预热
    cache_refresh_batch_size: int = 500         # 全量刷新时 Redis Pipeline 批次大小

    # --- CORS ---
    cors_origins: list[str] = ["http://localhost:5173"]  # 允许跨域的前端地址


settings = Settings()
