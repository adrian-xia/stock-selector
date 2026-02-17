## Why

V1 已完成 P4 板块数据的完整基础设施：8 张 raw 表、4 张业务表、8 个 fetch 方法、3 个 ETL 清洗函数和 4 个 DataManager 同步方法（sync_concept_index/daily/member + update_concept_indicators）。但盘后链路中尚未集成板块数据同步步骤，导致每日数据不会自动更新。P2 和 P3 已完成，P4 是数据采集体系完善的下一步。

## What Changes

- 盘后链路集成：在指数数据同步（步骤 3.6）之后增加板块数据同步步骤（步骤 3.7），调用已有的 sync_concept_index + sync_concept_daily + sync_concept_member + update_concept_indicators，失败不阻断后续链路
- 新增单元测试：覆盖 3 个 transform 函数（concept_index、concept_daily、concept_member）
- 文档更新：标记 P4 为"✅ V1 已实施"

## Capabilities

### New Capabilities
- `concept-sync`: P4 板块数据的盘后链路集成，支持每日自动同步板块基础信息、日线行情、成分股和技术指标

### Modified Capabilities
- `scheduler-jobs`: 盘后链路增加板块数据同步步骤（步骤 3.7）

## Impact

- **代码变更：** `app/scheduler/jobs.py`（盘后链路集成）
- **数据库：** 无 schema 变更（raw 表和业务表均已存在）
- **API：** 无变更
- **依赖：** 无新增依赖，复用现有 DataManager 方法
- **测试：** `tests/unit/test_etl.py` 新增 P4 ETL 转换测试
