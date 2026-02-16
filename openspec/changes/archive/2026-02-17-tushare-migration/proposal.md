## Why

BaoStock 和 AKShare 接口不稳定，频繁出现连接超时和数据缺失，严重影响每日盘后链路的可靠性。用户已购买 Tushare 6000 积分授权，Tushare 提供约 112 个股票/指数/板块相关接口，数据质量更高、接口更稳定，且支持按日期获取全市场数据（单次请求 ~5000 条），性能远优于逐只股票拉取的旧方案。

## What Changes

**BREAKING** 完全移除 BaoStock 和 AKShare 数据源，Tushare 作为唯一数据源：
- 删除 `app/data/baostock.py`、`app/data/akshare.py`、`app/data/pool.py`
- 新增 `app/data/tushare.py` — TushareClient（实现 DataSourceClient Protocol）

引入两层数据架构（raw → 业务表）：
- 新增 98 张 `raw_tushare_*` 原始表，每个 Tushare 接口一一对应一张 raw 表（排除实时接口、重复接口和不可用接口），字段与 API 输出完全一致
- 现有业务表（stock_daily, finance_indicator 等）保持不变，从 raw 表 ETL 清洗而来

新增指数和板块数据能力：
- 新增 `index_basic`、`index_daily`、`index_weight` 等指数业务表
- 新增 `concept_index`、`concept_daily`、`concept_member` 等板块业务表
- 支持申万/中信行业分类、同花顺/东方财富/通达信三个数据源的概念板块

同步模式变更：
- 旧模式：逐只股票 × 逐个日期（~5000 次 API/天）
- 新模式：逐个日期 × 全市场（~3-4 次 API/天），性能提升约 1000 倍

数据初始化：
- 测试环境从 2024-01-01 起，生产环境从 2006-01-01 起
- 所有数据全部重新初始化，不做迁移

扩展数据覆盖（6000 积分全部接口）：
- 融资融券、股东增减持、大宗交易、股权质押
- 龙虎榜机构明细、涨跌停列表、游资数据
- 筹码分布、技术面因子、券商盈利预测
- 沪深港通资金流向、板块资金流向

## Capabilities

### New Capabilities
- `tushare-client`: Tushare Pro API 客户端，令牌桶限流，asyncio.to_thread 异步包装，重试机制
- `raw-data-layer`: 原始数据表层，~30 张 raw_tushare_* 表，字段与 API 输出一一对应
- `tushare-etl`: Tushare 原始数据到业务表的 ETL 清洗转换层
- `index-data`: 指数基础信息、日线行情、成分权重、申万/中信行业分类
- `concept-board-data`: 概念/行业板块数据（同花顺/东方财富/通达信三源）
- `tushare-data-init`: 基于 Tushare 的全量数据初始化 CLI

### Modified Capabilities
- `data-source-clients`: **BREAKING** 移除 BaoStock/AKShare，TushareClient 作为唯一实现
- `data-manager`: sync 方法改用 TushareClient，新增按日期全市场同步模式
- `etl-pipeline`: 新增 transform_tushare_* 系列清洗函数，移除 clean_baostock_*/clean_akshare_*
- `batch-daily-sync`: 重写为按日期批量模式（不再逐只股票）
- `scheduler-jobs`: _build_manager 改用 TushareClient，盘后链路适配新同步模式
- `data-probe`: 数据嗅探改用 Tushare API
- `database-schema`: 新增 ~30 张 raw 表 + 指数/板块业务表
- `app-config`: 添加 tushare 配置，移除 baostock/akshare 配置
- `data-initialization`: 初始化流程改用 Tushare，支持 2006 年起全量拉取
- `baostock-connection-pool`: **BREAKING** 完全移除

## Impact

- **依赖变更**: 新增 `tushare>=1.4.0`，移除 `baostock`、`akshare`
- **数据库**: 新增 ~110 张表（98 raw + ~12 业务），现有 12 张业务表不变
- **配置**: `.env` 新增 `TUSHARE_TOKEN`，移除 BaoStock/AKShare 相关配置
- **API**: 对外 HTTP API 不变，策略引擎和回测引擎不变
- **测试**: 需要重写数据源相关的单元测试和集成测试
- **文档**: 需要更新设计文档、README、CLAUDE.md
