## Context

V1 已完成 P4 板块数据的完整基础设施：8 张 raw_tushare_* 表（ths_index/daily/member、dc_index/member/hot_new、tdx_index/member）、4 张业务表（concept_index/daily/member/technical_daily）、3 个 ETL 清洗函数（transform_tushare_concept_index/daily/member）和 4 个 DataManager 方法（sync_concept_index/daily/member + update_concept_indicators）。

当前盘后链路流程为：交易日历 → 股票列表 → 批量数据拉取 → 资金流向同步（P2） → 指数数据同步（P3） → 缓存刷新 → 完整性门控 → 策略管道。P4 板块数据同步需要插入到这个链路中。

与 P2/P3 不同，P4 的 DataManager 方法已经实现了完整的 API → raw → 业务表 流程（sync_concept_* 方法内部已包含 ETL），不需要单独的 etl_concept 方法。

## Goals / Non-Goals

**Goals:**
- 将已有的板块数据同步方法集成到盘后链路
- 补全 P4 ETL 清洗函数的单元测试
- 更新文档标记 P4 完成

**Non-Goals:**
- 不重构现有 DataManager 方法（已经可用）
- 不实现 dc_hot_new（东财热门概念）的日常同步（低优先级）
- 不实现数据校验测试（由后续变更统一实施）

## Decisions

**D1: 盘后链路只同步同花顺（THS）数据源的日线行情**

三个数据源中，同花顺覆盖最全、更新最及时。东财和通达信的板块基础信息和成分股可通过 CLI 手动同步。日线行情只同步 THS 源。

**D2: 板块基础信息和成分股为低频数据，不纳入每日盘后链路**

板块基础信息和成分股变动不频繁，通过初始化或 CLI 手动同步即可。盘后链路只同步日线行情和计算技术指标。

**D3: 板块数据同步插入盘后链路步骤 3.6 之后（指数数据同步后、缓存刷新前）**

与 P2/P3 一致，作为独立步骤插入，失败不阻断后续链路。

## Risks / Trade-offs

- [同花顺日线接口需要按 ts_code 逐个获取] → 板块数量有限（通常 200-300 个），使用已有 TokenBucket 限流，API 调用量可控
- [盘后链路步骤增多，总耗时增加] → 板块数据量远小于个股，预计增加数十秒
