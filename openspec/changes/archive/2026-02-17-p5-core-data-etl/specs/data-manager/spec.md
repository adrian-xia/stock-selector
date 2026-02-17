## MODIFIED Requirements

### Requirement: P5 核心数据同步方法
DataManager SHALL 提供 P5 核心扩展数据的同步方法集，包括约 20 张表的 raw 数据拉取和 2 张业务表的 ETL 清洗。所有 sync_raw 方法 SHALL 复用已有的 `_upsert_raw` 通用方法写入 raw 表。

#### Scenario: P5 同步方法可用
- **WHEN** 创建 DataManager 实例
- **THEN** 实例 SHALL 提供 sync_raw_suspend_d、sync_raw_limit_list_d、sync_raw_margin 等 P5 核心同步方法

#### Scenario: P5 ETL 方法可用
- **WHEN** 创建 DataManager 实例
- **THEN** 实例 SHALL 提供 etl_suspend、etl_limit_list 方法用于业务表清洗

#### Scenario: P5 聚合入口可用
- **WHEN** 创建 DataManager 实例
- **THEN** 实例 SHALL 提供 sync_p5_core 聚合方法，一次调用完成所有 P5 核心数据同步
