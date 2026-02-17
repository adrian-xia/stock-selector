## Why

V1 已完成 P3 指数数据 18 张 raw 表的建表、ORM 模型、TushareClient fetch 方法、6 个 ETL 清洗函数和 6 张业务表。但缺少 DataManager 同步方法和盘后链路集成，导致 raw 表和业务表始终为空，指数分析和行业轮动策略无法运行。P2 资金流向 ETL 已完成，P3 是数据采集体系完善的下一步。

## What Changes

- 新增 DataManager 同步方法：`sync_raw_index_basic`、`sync_raw_index_daily`、`sync_raw_index_weight`、`sync_raw_industry_classify`、`sync_raw_industry_member`、`sync_raw_index_technical` 从 Tushare API 获取数据写入 raw 表
- 新增 DataManager ETL 方法：`etl_index(trade_date)` 从 raw 表清洗写入业务表（index_basic、index_daily、index_weight、industry_classify、industry_member、index_technical_daily）
- 盘后链路集成：在资金流向同步（步骤 3.5）之后增加指数数据同步步骤（步骤 3.6），失败不阻断后续链路
- 新增单元测试：覆盖已有的 6 个 transform 函数
- 文档更新：标记 P3 为"✅ V1 已实施"

## Capabilities

### New Capabilities
- `index-etl`: P3 指数数据的 DataManager 同步方法，包括 raw 数据拉取和 ETL 清洗入库
- `index-sync`: P3 指数数据的盘后链路集成，支持每日自动同步指数行情、成分股权重、行业分类等

### Modified Capabilities
- `data-manager`: 新增 sync_raw_index_* 和 etl_index 方法
- `etl-pipeline`: ETL 清洗函数集扩展说明（函数已存在，需更新 spec 描述）
- `scheduler-jobs`: 盘后链路增加指数数据同步步骤

## Impact

- **代码变更：** `app/data/manager.py`（新增同步方法）、`app/scheduler/jobs.py`（盘后链路集成）
- **数据库：** 无 schema 变更（raw 表和业务表均已存在），仅新增数据写入逻辑
- **API：** 无变更
- **依赖：** 无新增依赖，复用现有 TushareClient 和 ETL 工具函数
- **测试：** `tests/unit/test_etl.py` 新增 P3 ETL 转换测试
