## Context

V1 已完成 P3 指数数据的完整基础设施：18 张 raw_tushare_* 表（Alembic 迁移）、ORM 模型（`app/models/raw.py`）、TushareClient fetch 方法（`app/data/tushare.py`）、6 个 ETL 清洗函数（`app/data/etl.py`）和 6 张业务表（`app/models/index.py`）。

当前盘后链路（`run_post_market_chain`）流程为：交易日历 → 股票列表 → 批量数据拉取 → 资金流向同步（P2） → 缓存刷新 → 完整性门控 → 策略管道。P3 指数数据同步需要插入到这个链路中。

P2 的 ETL 模式已经成熟：`sync_raw_*` 按日期获取数据写入 raw 表，`etl_*` 从 raw 表清洗写入业务表。P3 ETL 遵循相同模式。

## Goals / Non-Goals

**Goals:**
- 实现 DataManager 同步方法，支持按日期获取指数日线行情、成分股权重、指数技术因子写入 raw 表
- 实现 DataManager ETL 方法，从 raw 表清洗写入 6 张业务表
- 实现静态数据同步方法（指数基础信息、行业分类、行业成分股），支持全量刷新
- 集成到盘后链路，每日自动同步指数数据
- 补全 P3 ETL 清洗函数的单元测试

**Non-Goals:**
- 不实现 index_weekly/index_monthly 的日常同步（周线/月线可由日线聚合，按需手动同步）
- 不实现 index_dailybasic 的 ETL（无对应业务表，暂不需要）
- 不实现 sw_daily/ci_daily/tdx_daily 等多源指数日线的 ETL（标准 index_daily 接口已覆盖主流指数）
- 不实现 index_global/daily_info/sz_daily_info 的 ETL（全球指数和市场统计数据暂不需要）
- 不实现数据校验测试（由后续 `data-validation-tests` 变更统一实施）

## Decisions

**D1: 只 ETL 核心 6 类数据（index_basic + index_daily + index_weight + index_classify + index_member_all + index_factor_pro），其余 12 张 raw 表暂不处理**

18 张 raw 表中，核心 6 类覆盖了指数行情、成分股、行业分类和技术因子，满足指数分析和行业轮动策略需求。其余表是不同数据源版本（申万/中证/通达信）或低频数据（周线/月线/全球指数），当前无对应业务表或可由核心数据推导。

**D2: 区分日常同步数据和静态数据**

- 日常同步（每日盘后）：index_daily、index_weight、index_factor_pro — 按 trade_date 获取当日数据
- 静态数据（低频更新）：index_basic、index_classify、index_member_all — 全量刷新，不纳入盘后链路，通过 CLI 或初始化时同步

**D3: 指数数据同步插入盘后链路步骤 3.5 之后（资金流向同步后、缓存刷新前）**

指数数据不影响个股技术指标计算和策略管道核心流程。作为独立步骤插入，失败不阻断后续链路。

**D4: index_daily 按 trade_date 批量获取需要遍历核心指数列表**

与个股日线不同，Tushare index_daily 接口不支持按 trade_date 获取全市场数据，需要按 ts_code 逐个获取。维护一个核心指数列表（上证综指、深证成指、创业板指、沪深300、中证500、中证1000 等），每日遍历获取。

**D5: 复用现有 ETL 工具函数和 P2 同步模式**

使用 `parse_date()`、`parse_decimal()`、`_upsert_raw()`、`batch_insert()` 等已有工具函数，保持代码风格一致。

## Risks / Trade-offs

- [index_daily 按 ts_code 获取，API 调用次数较多] → 核心指数列表控制在 10-20 个，每日 API 调用量可控；使用已有 TokenBucket 限流
- [index_weight 数据量较大（每个指数数百只成分股）] → 按 index_code 逐个获取，使用 UPSERT 避免重复
- [静态数据更新频率不确定] → 初始化时全量同步，后续可通过 CLI 手动触发刷新
