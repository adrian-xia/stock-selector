## Context

这是一个全新项目（空仓库），数据采集模块是第一个要实现的模块。没有现有代码、没有数据库、没有配置体系。本次变更需要从零搭建项目骨架（配置、数据库连接、ORM 模型）以及完整的数据采集链路。

当前约束：
- 单机部署、单人使用，不需要分布式架构
- V1 阶段：去掉 raw 中转层、故障切换状态机、TimescaleDB 分区、断点续传、数据质量报告
- 数据源仅 BaoStock（主）+ AKShare（备），Tushare 暂不接入（V1 财务数据从 BaoStock 获取）
- BaoStock 是同步阻塞 API，需要在 async 环境中用线程池包装

## Goals / Non-Goals

**Goals:**
- 搭建项目基础骨架：配置加载、数据库连接、ORM 模型、日志
- 实现 BaoStock 和 AKShare 两个数据源客户端，遵循统一接口
- 实现 ETL 清洗管道，将异构数据标准化入库
- 实现 DataManager 统一数据访问层，供后续策略引擎和回测引擎调用
- 创建 12 张 V1 数据库表（通过 Alembic 迁移）
- 提供全量导入 CLI 脚本和增量同步函数
- 所有 IO 操作使用 async/await

**Non-Goals:**
- 不实现 raw 中转层（直接清洗入标准表）
- 不实现断点续传（`import_progress` 表），失败重跑即可
- 不实现数据质量报告系统（`data_quality_report` 表）
- 不实现故障切换状态机，仅做简单的主备 fallback
- 不实现 TimescaleDB 分区，使用普通 PostgreSQL 表
- 不实现 Tushare 客户端（V2 再加）
- 不实现 Redis 缓存层（后续变更处理）
- 不实现定时任务调度（后续变更处理）
- 不实现 HTTP API 端点（后续变更处理）

## Decisions

### D1: 项目结构 — 扁平模块 vs 分层包

**选择：** 按功能域分包，每个包内文件扁平

```
app/
├── __init__.py
├── main.py              # FastAPI 入口（本次仅创建骨架）
├── config.py            # pydantic-settings 配置
├── logger.py            # logging 配置
├── database.py          # 引擎 + 会话工厂
├── models/              # SQLAlchemy ORM 模型
│   ├── __init__.py      # 导出所有模型
│   ├── base.py          # DeclarativeBase
│   ├── market.py        # TradeCalendar, Stock, StockDaily, StockMin
│   ├── finance.py       # FinanceIndicator
│   ├── technical.py     # TechnicalDaily
│   ├── flow.py          # MoneyFlow, DragonTiger
│   ├── strategy.py      # Strategy, DataSourceConfig
│   └── backtest.py      # BacktestTask, BacktestResult
├── data/                # 数据采集模块
│   ├── __init__.py
│   ├── client_base.py   # DataSourceClient Protocol
│   ├── baostock.py      # BaoStockClient
│   ├── akshare.py       # AKShareClient
│   ├── etl.py           # ETL 清洗函数
│   ├── manager.py       # DataManager
│   └── cli.py           # CLI 入口
└── exceptions.py        # 自定义异常
```

**理由：** 项目初期文件不多，过深的嵌套增加导入复杂度。按功能域分包（models、data）已足够清晰，后续模块（strategy、backtest、ai）各自成包。

### D2: 数据源客户端接口 — Protocol vs ABC

**选择：** 使用 `typing.Protocol`（结构化子类型）

```python
class DataSourceClient(Protocol):
    async def fetch_daily(self, code: str, start_date: date, end_date: date) -> list[dict]: ...
    async def fetch_stock_list(self) -> list[dict]: ...
    async def fetch_trade_calendar(self, start_date: date, end_date: date) -> list[dict]: ...
    async def health_check(self) -> bool: ...
```

**理由：** Protocol 不要求显式继承，更 Pythonic。BaoStock 和 AKShare 的实现差异较大（一个需要 login/logout，一个不需要），Protocol 比 ABC 更灵活。类型检查器（mypy/pyright）可以静态验证接口一致性。

**备选方案：** ABC + `@abstractmethod`。优点是运行时强制检查，但对于两个实现类来说 Protocol 已足够。

### D3: BaoStock 同步 API 的异步包装

**选择：** 使用 `asyncio.to_thread()` 将 BaoStock 的同步调用放到线程池

```python
async def fetch_daily(self, code, start_date, end_date):
    return await asyncio.to_thread(self._fetch_daily_sync, code, start_date, end_date)
```

**理由：** BaoStock 的 Python SDK 是纯同步的（内部用 socket），无法直接 await。`asyncio.to_thread()` 是 Python 3.9+ 标准方案，比手动管理 `ThreadPoolExecutor` 更简洁。每次调用在独立线程中执行 login → query → logout，避免线程间共享 BaoStock 连接状态。

**备选方案：** 进程池（`ProcessPoolExecutor`）。开销更大，BaoStock 不是 CPU 密集型，线程池足够。

### D4: ETL 清洗 — 类 vs 纯函数

**选择：** 纯函数模块 `etl.py`，每个清洗步骤是一个独立函数

```python
def normalize_stock_code(raw_code: str, source: str) -> str: ...
def parse_decimal(value: str | None) -> Decimal | None: ...
def parse_date(value: str | None) -> date | None: ...
def clean_baostock_daily(raw_rows: list[dict]) -> list[dict]: ...
def clean_akshare_daily(raw_df: pd.DataFrame) -> list[dict]: ...
```

**理由：** ETL 清洗是无状态的数据转换，纯函数更易测试、更易组合。不需要类的实例状态。每个数据源有自己的 `clean_*` 函数，内部调用共享的工具函数（normalize_stock_code、parse_decimal 等）。

### D5: DataManager — 组合数据源客户端

**选择：** DataManager 持有所有客户端实例，通过 `primary_source` 配置决定默认使用哪个

```python
class DataManager:
    def __init__(self, session_factory, clients: dict[str, DataSourceClient], primary: str = "baostock"):
        self._session_factory = session_factory
        self._clients = clients
        self._primary = primary
```

Fallback 逻辑：主源失败 → 日志 warning → 尝试备源 → 备源也失败 → 抛异常。不做自动切换状态机。

**理由：** V1 简化方案。单人使用场景下，数据源故障是低频事件，简单 fallback + 日志足够。状态机增加复杂度但收益有限。

### D6: 数据库批量写入策略

**选择：** SQLAlchemy Core `insert().values([...]).on_conflict_do_nothing()`，每批 5000 行

**理由：**
- `on_conflict_do_nothing` 天然支持幂等重跑，无需断点续传表
- SQLAlchemy Core 的批量 insert 比 ORM `session.add_all()` 快 5-10 倍
- 5000 行/批是 PostgreSQL 的合理批次大小，平衡内存和网络开销

**备选方案：** PostgreSQL `COPY FROM`（更快 10 倍）。V1 先用 insert，如果全量导入性能不够再切换到 COPY。

### D7: Alembic 迁移策略

**选择：** 使用 Alembic 的 `--autogenerate` 生成初始迁移，包含全部 12 张表

迁移文件结构：
```
alembic/
├── alembic.ini
├── env.py          # 配置 async engine
└── versions/
    └── 001_initial_schema.py
```

**理由：** 虽然 V1 范围说"手动管理 schema"，但 Alembic 的初始成本很低（一次配置），后续模块加表时可以增量迁移，比手动执行 SQL 文件更可靠。

### D8: 配置体系 — 扁平 vs 嵌套 Settings

**选择：** 单一扁平 `Settings` 类，使用前缀区分模块

```python
class Settings(BaseSettings):
    # Database
    database_url: str
    db_pool_size: int = 5
    # BaoStock
    baostock_retry_count: int = 3
    baostock_timeout: int = 30
    # AKShare
    akshare_retry_count: int = 3
    ...
    model_config = SettingsConfigDict(env_file=".env")
```

**理由：** 嵌套 Settings（BaoStockConfig、AKShareConfig 等）在 pydantic-settings v2 中需要额外的 `env_nested_delimiter` 配置，且 `.env` 文件中的变量名会变成 `BAOSTOCK__RETRY_COUNT`（双下划线），不够直观。扁平结构更简单，`.env` 中直接写 `BAOSTOCK_RETRY_COUNT=3`。

### D9: CLI 工具 — click vs argparse

**选择：** 使用 `click`

**理由：** click 已是 Python CLI 事实标准，语法比 argparse 简洁。项目已依赖 FastAPI（间接依赖 click via uvicorn），不增加额外依赖。支持子命令分组，适合 `import-all`、`import-daily`、`sync-daily` 等多命令场景。

### D10: 日志配置

**选择：** Python 标准 `logging` 模块，配置为 JSON 格式输出到文件 + 控制台

```python
# app/logger.py
import logging
import sys

def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("logs/app.log"),
        ],
    )
```

**理由：** V1 不需要 ELK/Loki，文件日志 + 控制台输出足够。后续可以替换 handler 接入结构化日志。

## Risks / Trade-offs

### R1: BaoStock 数据完整性无法保证
- **风险：** BaoStock 是免费数据源，偶尔会出现数据缺失或延迟更新
- **缓解：** AKShare 作为备源；全量导入使用 `ON CONFLICT DO NOTHING` 支持幂等重跑；后续 V2 加入数据质量检查

### R2: 无断点续传，全量导入失败需重跑
- **风险：** 全量导入 5000+ 只股票可能耗时数小时，中途失败需要从头开始
- **缓解：** `ON CONFLICT DO NOTHING` 保证已入库的数据不会重复插入，重跑时只有新数据会被写入，实际耗时主要在 API 调用而非数据库写入。可以按数据类型分步执行（先 stocks，再 calendar，再 daily）

### R3: BaoStock 同步 API 在线程池中的并发限制
- **风险：** BaoStock 的 login/logout 是全局状态，多线程并发可能冲突
- **缓解：** 每次 `to_thread` 调用内部独立 login/logout，不共享连接。QPS 限流（默认 5/s）控制并发度

### R4: 无 Redis 缓存，查询性能依赖数据库索引
- **风险：** 策略引擎高频调用 `get_daily_bars()` 时，全部走数据库查询
- **缓解：** V1 表结构已设计了合理的复合索引（ts_code + trade_date DESC）。单股票 1 年数据查询在 PostgreSQL 上通常 < 50ms。Redis 缓存层在后续变更中加入

### R5: 扁平 Settings 在配置项增多后可能变得冗长
- **风险：** 随着模块增加，单一 Settings 类可能有 50+ 个字段
- **缓解：** 可以在后续重构为嵌套结构。当前 V1 只有数据采集模块的配置，扁平结构完全可控

## Open Questions

- **Q1:** 分钟线数据（`stock_min`）是否在 V1 第一个变更中导入？建议先跳过，聚焦日线数据，分钟线作为后续变更。
- **Q2:** `finance_indicator` 的数据源——BaoStock 的财务数据覆盖度是否足够？如果不够，可能需要提前引入 Tushare。
