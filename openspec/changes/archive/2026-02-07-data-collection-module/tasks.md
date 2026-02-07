## 1. 项目骨架与配置

- [x] 1.1 创建项目目录结构（app/, app/models/, app/data/, tests/）和 `__init__.py` 文件
- [x] 1.2 配置 `pyproject.toml`：添加所有依赖（fastapi, uvicorn, sqlalchemy[asyncio], asyncpg, pydantic-settings, baostock, akshare, alembic, click, pandas）
- [x] 1.3 实现 `app/config.py`：扁平 Settings 类，包含 DATABASE_URL、DB_POOL_SIZE、BAOSTOCK_*、AKSHARE_*、ETL_*、LOG_LEVEL 等配置项
- [x] 1.4 更新 `.env.example`：列出所有配置变量及示例值和注释
- [x] 1.5 实现 `app/logger.py`：setup_logging() 函数，控制台 + 文件输出
- [x] 1.6 实现 `app/exceptions.py`：定义 DataSourceError、DataSyncError、InvalidCodeError 等自定义异常

## 2. 数据库连接与 ORM 模型

- [x] 2.1 实现 `app/database.py`：async engine 创建、async_sessionmaker、get_db_session() 上下文管理器
- [x] 2.2 实现 `app/models/base.py`：SQLAlchemy DeclarativeBase
- [x] 2.3 实现 `app/models/market.py`：TradeCalendar、Stock、StockDaily、StockMin 模型（对应 database-schema spec 中的 DDL）
- [x] 2.4 实现 `app/models/finance.py`：FinanceIndicator 模型
- [x] 2.5 实现 `app/models/technical.py`：TechnicalDaily 模型
- [x] 2.6 实现 `app/models/flow.py`：MoneyFlow、DragonTiger 模型
- [x] 2.7 实现 `app/models/strategy.py`：Strategy、DataSourceConfig 模型
- [x] 2.8 实现 `app/models/backtest.py`：BacktestTask、BacktestResult 模型
- [x] 2.9 实现 `app/models/__init__.py`：统一导出所有模型
- [x] 2.10 配置 Alembic：alembic.ini + async env.py，生成初始迁移（12 张表）

## 3. 数据源客户端

- [x] 3.1 实现 `app/data/client_base.py`：DataSourceClient Protocol 定义（fetch_daily, fetch_stock_list, fetch_trade_calendar, health_check）
- [x] 3.2 实现 `app/data/baostock.py`：BaoStockClient — login/logout 管理、fetch_daily（asyncio.to_thread 包装）、fetch_stock_list、fetch_trade_calendar、health_check
- [x] 3.3 实现 `app/data/akshare.py`：AKShareClient — fetch_daily（stock_zh_a_hist）、fetch_stock_list、fetch_trade_calendar、health_check
- [x] 3.4 为两个客户端实现重试退避逻辑（retry_count 次，间隔 retry_interval * 2^attempt）
- [x] 3.5 为两个客户端实现 QPS 限流（asyncio.Semaphore 或令牌桶）

## 4. ETL 清洗管道

- [x] 4.1 实现 `app/data/etl.py` 工具函数：normalize_stock_code()、parse_decimal()、parse_date()
- [x] 4.2 实现 clean_baostock_daily()：BaoStock 日线数据清洗（代码转换、类型转换、trade_status 标准化、data_source 标记）
- [x] 4.3 实现 clean_akshare_daily()：AKShare 日线数据清洗（中文列名映射、代码推断交易所、类型转换）
- [x] 4.4 实现 clean_baostock_stock_list()：股票列表清洗
- [x] 4.5 实现 clean_baostock_trade_calendar()：交易日历清洗
- [x] 4.6 实现 batch_insert() 通用函数：接收表对象和 list[dict]，执行 insert().values().on_conflict_do_nothing()，按 batch_size 分批

## 5. DataManager 统一数据访问层

- [x] 5.1 实现 `app/data/manager.py` DataManager 类骨架：__init__（session_factory, clients, primary）
- [x] 5.2 实现 sync_stock_list()：从数据源获取股票列表 → ETL 清洗 → 批量写入 stocks 表
- [x] 5.3 实现 sync_trade_calendar()：从数据源获取交易日历 → ETL 清洗 → 批量写入 trade_calendar 表
- [x] 5.4 实现 sync_daily()：从数据源获取全部股票日线 → ETL 清洗 → 批量写入 stock_daily 表，含主备 fallback 逻辑
- [x] 5.5 实现 get_daily_bars()：从 stock_daily 查询数据，支持 qfq/hfq/none 三种复权计算，返回 DataFrame
- [x] 5.6 实现 get_stock_list()：从 stocks 表查询，支持按 list_status 过滤
- [x] 5.7 实现 get_trade_calendar()：从 trade_calendar 表查询交易日列表
- [x] 5.8 实现 is_trade_day()：判断指定日期是否为交易日

## 6. CLI 导入脚本

- [x] 6.1 实现 `app/data/cli.py`：click 命令组骨架
- [x] 6.2 实现 `import-stocks` 子命令：调用 DataManager.sync_stock_list()
- [x] 6.3 实现 `import-calendar` 子命令：调用 DataManager.sync_trade_calendar()
- [x] 6.4 实现 `import-daily` 子命令：遍历所有股票，逐只调用 fetch_daily + ETL + batch_insert，每 100 只输出进度日志，支持 --optimize-indexes 参数
- [x] 6.5 实现 `import-all` 子命令：按顺序执行 import-stocks → import-calendar → import-daily
- [x] 6.6 实现 `sync-daily` 子命令：增量同步当日数据（检查是否交易日 → 获取当日数据 → 入库）

## 7. FastAPI 入口骨架

- [x] 7.1 实现 `app/main.py`：FastAPI app 创建、startup/shutdown 事件（初始化 engine、dispose engine）、health check 端点

## 8. 测试

- [x] 8.1 编写 ETL 工具函数单元测试：normalize_stock_code、parse_decimal、parse_date 的各种边界情况
- [x] 8.2 编写 ETL 清洗函数单元测试：clean_baostock_daily、clean_akshare_daily 使用 mock 数据验证输出格式
- [x] 8.3 编写 DataManager 单元测试：get_daily_bars 复权计算逻辑（mock 数据库查询）
- [x] 8.4 编写集成测试：验证 Alembic 迁移能正确创建所有 12 张表（使用测试数据库）
