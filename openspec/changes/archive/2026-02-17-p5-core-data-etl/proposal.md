## Why

P5 扩展数据的 48 张 raw 表和 fetch 方法已全部就位（仅建表状态），但缺少 ETL 同步逻辑和盘后链路集成。核心的约 20 张表（停复牌、涨跌停、两融、股东、技术因子等）直接影响交易决策和策略增强，需要优先实现数据流转，使这些数据从"有表无数据"变为"每日自动更新"。

## What Changes

- 新增约 20 张 P5 核心 raw 表的 DataManager 同步方法（`sync_raw_xxx`），复用已有的 `_upsert_raw` 通用方法
- 为停复牌（suspend_d）和涨跌停统计（limit_list_d）创建业务表及 ETL transform 函数，其余表直接查询 raw 表
- 盘后链路新增步骤 3.8（P5 核心数据同步），按同步频率分组调度（日频/周频/月频/静态）
- 新增 Alembic 迁移脚本创建业务表

## Capabilities

### New Capabilities
- `p5-core-etl`: P5 核心扩展数据的 ETL 同步能力，包括约 20 张表的 raw 数据拉取、2 张业务表的 ETL 清洗、按频率分组的同步调度

### Modified Capabilities
- `scheduler-jobs`: 盘后链路新增步骤 3.8，集成 P5 核心数据同步
- `data-manager`: DataManager 新增 P5 相关的 sync_raw / etl 方法

## Impact

- **代码文件**：`app/data/manager.py`（新增同步方法）、`app/data/etl.py`（新增 transform 函数）、`app/scheduler/jobs.py`（盘后链路集成）
- **数据库**：新增 2 张业务表（suspend_info、limit_list_daily），需 Alembic 迁移
- **模型文件**：`app/models/` 新增业务表 ORM 模型
- **依赖**：无新增外部依赖，复用现有 Tushare/SQLAlchemy 基础设施
- **影响范围**：不影响现有 P0-P4 数据流，P5 步骤失败不阻断盘后链路
