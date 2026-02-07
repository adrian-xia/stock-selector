## Why

系统的所有功能（策略筛选、回测、AI 分析）都依赖高质量的 A 股行情和财务数据。当前项目是空仓库，没有任何数据采集能力。数据采集是整个系统的地基，必须最先实现。

## What Changes

- 新增 BaoStock 数据源客户端，支持获取日线行情、股票列表、交易日历
- 新增 AKShare 数据源客户端，作为备用数据源
- 新增 ETL 清洗层，将不同数据源的异构数据标准化为统一格式
- 新增 DataManager 统一数据访问接口，屏蔽底层数据源差异
- 新增 PostgreSQL 标准层表结构（stock_daily, stocks, trade_calendar, finance_indicator, technical_daily 等）
- 新增数据库连接和 SQLAlchemy 异步会话管理
- 新增 pydantic-settings 配置加载（.env 文件）
- 新增全量导入脚本（首次初始化历史数据）
- 新增增量更新逻辑（每日收盘后同步当天数据）

## Capabilities

### New Capabilities
- `data-source-clients`: BaoStock 和 AKShare 数据源客户端，统一接口（fetch_daily, fetch_stock_list, health_check），支持主备切换
- `etl-pipeline`: 数据清洗与标准化，字段映射、类型转换、异常值处理、复权因子保留
- `data-manager`: 统一数据访问层，提供 get_daily_bars(adj='qfq')、get_stock_list()、get_trade_calendar() 等接口
- `database-schema`: PostgreSQL 标准层 DDL（trade_calendar, stocks, stock_daily, stock_min, finance_indicator, technical_daily, money_flow, dragon_tiger, data_source_configs, strategies, backtest_tasks, backtest_results）
- `database-connection`: SQLAlchemy 异步引擎 + 会话管理 + Alembic 初始迁移
- `app-config`: pydantic-settings 配置加载，从 .env 读取数据库/Redis/API Key 等配置
- `data-import-scripts`: 全量导入脚本（历史日线、股票列表、交易日历、财务指标）和增量更新逻辑

### Modified Capabilities
<!-- 空项目，无已有 capability -->

## Impact

- **新增依赖：** fastapi, uvicorn, sqlalchemy[asyncio], asyncpg, pydantic-settings, baostock, akshare, alembic, redis
- **数据库：** 需要本地 PostgreSQL 实例，创建 stock_selector 数据库
- **外部 API：** BaoStock（免费，无需 Token）、AKShare（免费，无需 Token）、Tushare（需 Token，用于财务数据）
- **磁盘：** 全量历史日线约 2-3 GB，分钟线约 10-20 GB（V1 可选）
- **后续模块依赖：** 策略引擎、回测引擎、缓存层、定时任务调度均依赖本模块提供的数据
