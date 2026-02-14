## Context

当前系统使用 BaoStock（主）+ AKShare（备）作为数据源，通过 `DataSourceClient` Protocol 抽象。BaoStock 采用逐只股票拉取模式，5000 只股票每天需要 ~5000 次 API 调用，且连接不稳定。用户已购买 Tushare 6000 积分，覆盖约 112 个股票/指数/板块接口。

现有架构：数据源 → ETL 清洗 → 业务表（直接写入，无中间层）。
目标架构：TushareClient → raw 原始表 → ETL 清洗 → 业务表。

关键约束：
- DataManager 公开方法签名不变，策略引擎和回测引擎零修改
- Tushare SDK 是同步的，需要 `asyncio.to_thread` 包装
- 基础积分 500 次/分钟限流
- 历史数据：测试环境 2024 起，生产环境 2006 起

## Goals / Non-Goals

**Goals:**
- 完全替换 BaoStock/AKShare，Tushare 作为唯一数据源
- 引入 raw 原始数据层，保留 API 原始返回，便于数据溯源和重新清洗
- 覆盖 6000 积分可用的全部股票/指数/板块接口（98 张 raw 表一一对应）
- 新增指数数据和概念板块数据能力
- 每日同步从 ~5000 次 API 降至 ~10 次 API

**Non-Goals:**
- 不修改策略引擎和回测引擎
- 不修改前端和 HTTP API
- 不做数据迁移（全部重新初始化）
- 不接入期货/期权/债券/基金等非股票数据
- 不实现实时行情（爬虫版接口暂不接入）

## Decisions

### D1: 按日期全市场同步 vs 逐只股票同步

**选择**: 按日期全市场同步

Tushare `daily(trade_date='20260214')` 一次返回全市场 ~5000 条数据。相比逐只股票拉取，API 调用次数从 ~5000 次/天降至 3-4 次/天。

替代方案：保持逐只股票模式 — 浪费 API 配额，无法利用 Tushare 的批量优势。

### D2: 原始表设计 — 宽表 vs 窄表

**选择**: 宽表，每个 Tushare 接口对应一张 raw 表

字段与 API 输出一一对应，VARCHAR 存储日期（保持 YYYYMMDD 原始格式），NUMERIC 存储数值。不做任何转换，ETL 层负责类型转换和字段映射。

替代方案：JSON 列存储 — 查询不便，无法建索引。

### D3: TushareClient 实现 DataSourceClient Protocol

**选择**: TushareClient 同时实现 Protocol 的 4 个方法（向后兼容）+ 扩展的 `fetch_raw_*` 方法（原始数据获取）

Protocol 方法内部调用 `fetch_raw_*` 获取原始数据，再通过 ETL 转换为业务格式返回。这样 DataManager 的现有代码可以最小改动。

### D4: 限流策略 — 令牌桶

**选择**: 令牌桶算法，速率 8 次/秒（480 次/分钟，留 20% 余量）

Tushare 限流是每分钟 500 次。令牌桶比固定窗口更平滑，避免突发请求被拒。

### D5: 同步 SDK 异步化

**选择**: `asyncio.to_thread` 包装每次 API 调用

Tushare SDK 内部使用 requests 库，是同步阻塞的。`to_thread` 将其放入线程池执行，不阻塞事件循环。

替代方案：直接调用 Tushare HTTP API（绕过 SDK）— 需要自行处理认证和数据解析，维护成本高。

### D6: 财务数据获取策略 — VIP 接口优先

**选择**: 使用 `fina_indicator_vip`（5000 积分）按季度获取全部公司

标准 `fina_indicator` 只能按单只股票获取历史，5000 只股票需要 5000 次调用。VIP 版按 `period` 参数获取某季度全部公司数据，约 20 次调用覆盖 5 年数据。

### D7: 指数和板块数据 — 统一业务表 + 数据源标记

**选择**: 概念板块使用统一的 `concept_index` / `concept_daily` / `concept_member` 业务表，通过 `source` 字段区分同花顺/东方财富/通达信

替代方案：每个数据源独立表 — 查询时需要 UNION，不便于统一分析。

### D8: 指数和板块技术指标 — 独立表 + 复用计算引擎

**选择**: 为指数和板块各新增独立的技术指标表（`index_technical_daily` / `concept_technical_daily`），字段结构与现有 `technical_daily` 完全一致（23 个指标），复用 `indicator.py` 的计算函数。

指数和板块的行情数据（index_daily / concept_daily）包含 OHLCV，具备计算技术指标的全部输入。独立表的好处：
- 不与个股指标混在一起，查询更清晰
- 可以独立控制计算频率和回溯窗口
- 未来可以扩展指数/板块特有的指标

替代方案：复用 `technical_daily` 表，通过 ts_code 前缀区分 — 会导致表膨胀，且索引效率下降。

### D9: 数据初始化 — 按日期循环 + 进度追踪

**选择**: 复用现有 `stock_sync_progress` 表的断点续传机制，但粒度从"每只股票"改为"每个交易日"

新增 `raw_sync_progress` 表追踪原始数据拉取进度，支持中断后从上次位置继续。

## Risks / Trade-offs

**[Tushare 服务不可用]** → 无备用数据源。Tushare 是付费服务，稳定性远高于免费的 BaoStock/AKShare。如果确实需要备用，可以后续接入其他付费源。

**[API 限流导致初始化慢]** → 全量初始化（2006 年起）约 5000 个交易日 × 3-4 次/天 = ~20000 次 API 调用，按 480 次/分钟约 42 分钟。加上数据库写入，预计 1-2 小时。可接受。

**[raw 表占用存储空间]** → 98 张 raw 表，每张存储全量历史。估算：daily 表 5000 股 × 5000 天 = 2500 万行，约 2-3 GB；全部 raw 表合计预计 10-20 GB。PostgreSQL 单机完全可以承受。

**[amount 单位不一致]** → Tushare daily 的 amount 单位是千元，现有 stock_daily 的 amount 单位需要确认。ETL 层统一处理。

**[复权因子差异]** → Tushare adj_factor 是后复权因子（基期为上市日），与 BaoStock 一致。现有回测引擎的前复权公式 `price * (adj/latest_adj)` 兼容。

## Migration Plan

1. 创建新分支 `feat/tushare-migration`
2. Phase 0-1: 基础设施 + P0 核心数据 → 验证策略和回测正常
3. Phase 2-3: 财务 + 资金流向 → 验证基本面策略正常
4. Phase 4-5: 指数 + 板块 → 新能力验证
5. Phase 6: 扩展数据 → 按需实施
6. Phase 7: 数据初始化 CLI → 端到端验证
7. Phase 8: 文档更新 + 清理 → 合并到 master

回滚策略：保留 BaoStock/AKShare 代码直到 Phase 1 验证通过后再删除。

## Open Questions

1. `stock_daily.amount` 现有单位是什么？需要确认 ETL 转换逻辑
2. 是否需要保留 `data_source_configs` 表？切换到单一数据源后可能不再需要
