## Why

当前系统存在两条数据写入路径：启动同步 `sync_from_progress` 和 `process_stocks_batch` 直接写入业务表（stock_daily），绕过了 raw 层；而盘后链路的 P2-P5 步骤走的是 raw-first 路径。这导致 raw_tushare_daily 等 P0 raw 表只有少量数据（24 万行 vs stock_daily 374 万行），raw 层无法作为可靠的数据基础。需要统一为 raw-first 架构：所有数据必须先写入 raw 表，再通过 ETL 清洗到业务表，使 raw 层成为全量、最新、可追溯的数据基础，支撑任意维度的数据处理和预测。

## What Changes

- **统一数据写入路径为 raw-first**：所有数据链路（初始化、盘后增量、断点续传、失败重试）统一为 `API → raw_* → ETL → 业务表` 的单一流程，区别仅在于"哪些表、哪些日期需要同步"。核心同步和 ETL 逻辑高度复用，消除当前多条并行路径导致的代码重复和数据不一致
- **统一同步入口**：抽象出通用的 `sync_raw_and_etl(tables, date_range)` 方法，数据初始化、盘后增量、断点续传、失败重试全部调用同一入口，仅传入不同的表范围和日期范围
- **启动同步补全 raw 表**：启动时检测 raw_* 表的数据缺口，自动补全历史数据到 raw 表，再通过 ETL 刷新业务表
- **盘后链路全量追平 raw 表**：每日盘后处理确保所有 raw_* 表（P0-P5）追到最新交易日，不仅限于当天数据
- **数据初始化脚本 raw-first 化**：`scripts/init_data.py` 以 raw 表为驱动，复用统一同步入口，先全量写入 raw 表，再批量 ETL 到业务表
- **raw 表数据缺口检测**：新增 raw 表完整性检查机制，识别各 raw 表的日期缺口并自动补齐
- **P1 财务数据 ETL 补全**：当前 P1 只实现了 fina_indicator 的 ETL，需补全 income/balancesheet/cashflow 等表的 ETL
- **ETL 写入策略统一**：`batch_insert` 从 `ON CONFLICT DO NOTHING` 改为 `ON CONFLICT DO UPDATE`，确保 Tushare 历史数据修正能同步到业务表

## 已知问题（数据同步测试中发现）

以下问题需在本次变更中一并修复：

1. **COPY 协议始终失败**：临时表 `_tmp_*` 不存在，每次都降级到 INSERT，严重影响批量写入性能
2. **P3 `index_factor_pro` 接口不可用**：Tushare 返回"请指定正确的接口名"，需确认正确接口名或移除
3. **P3 `industry_classify` 返回 0 行**：API 调用成功但无数据返回，需排查参数或数据源问题
4. **P3 `industry_member` null 主键**：`index_code` 为 null 导致写入 `raw_tushare_index_member_all` 失败
5. **P4 `concept_member` 未同步**：需要逐个板块同步成分股，当前盘后链路未包含此步骤
6. **P4 `concept_technical_daily` 未计算**：板块技术指标依赖 concept_daily 数据，需在盘后链路中补充
7. **P5 12 项同步失败**：daily_share、hm_board、hm_list、ths_limit、hsgt_top10、ccass_hold_detail、cyq_chips、limit_step、hm_detail、stk_auction_o、kpl_concept、broker_recommend — 原因包括接口权限、参数错误、列名不匹配等
8. **P1 财务数据盘后链路无步骤**：盘后链路缺少 P1 财务数据同步步骤（步骤 3.x）
9. **P4 板块 ETL 不完整**：只实现了 concept_index 基础信息，concept_member 的 ETL 转换缺失
10. **股票列表和交易日历绕过 raw 表**：`sync_stock_list` 和 `sync_trade_calendar` 直接写业务表（stocks、trade_calendar），不经过 raw_tushare_stock_basic / raw_tushare_trade_cal，与 raw-first 设计原则不一致
11. **batch_insert 使用 DO NOTHING 而非 DO UPDATE**：业务表写入时冲突跳过而非更新，导致 Tushare 历史数据修正无法同步到业务表

## Capabilities

### New Capabilities
- `raw-data-gap-detection`: raw 表数据缺口检测与自动补齐机制，支持按表、按日期范围识别缺失数据并触发补同步
- `raw-first-daily-sync`: 统一 P0 日线数据的 raw-first 写入路径，替代当前直接写 stock_daily 的方式

### Modified Capabilities
- `data-initialization`: 数据初始化脚本改为 raw-first 驱动，先写 raw 表再 ETL
- `batch-daily-sync`: process_stocks_batch 改为 raw-first 路径
- `scheduler-jobs`: 盘后链路增加 raw 表全量追平逻辑
- `etl-pipeline`: 补全 P1 财务数据的 ETL 转换函数，统一写入策略为 DO UPDATE
- `stock-data-completeness-check`: 完整性检查扩展到覆盖 raw 表

## Impact

- **核心代码变更**：`app/data/manager.py`（统一同步入口、sync_from_progress、process_stocks_batch、raw 缺口检测）、`app/scheduler/jobs.py`（盘后链路 raw 追平）、`app/scheduler/core.py`（启动同步逻辑）
- **ETL 扩展**：`app/data/etl.py` 补全 P1 财务 ETL 函数，`batch_insert` 统一为 DO UPDATE
- **初始化脚本**：`scripts/init_data.py` 重构为 raw-first 流程
- **数据库**：raw_* 表成为全量数据源，业务表完全由 ETL 派生
- **性能考量**：raw 表全量补齐涉及大量 API 调用和数据写入，需要合理的批次控制和断点续传；COPY 协议临时表问题需修复以提升写入性能
- **向后兼容**：业务表结构不变（仅新增约束），API 接口不变，前端无感知
