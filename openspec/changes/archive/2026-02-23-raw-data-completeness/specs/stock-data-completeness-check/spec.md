## MODIFIED Requirements

### Requirement: 完整性检查覆盖 raw 表
数据完整性检查 SHALL 扩展到覆盖所有 raw_* 表，不仅限于 stock_daily 业务表。

#### Scenario: 启动时检查 raw 表完整性
- **WHEN** 系统启动且 DATA_INTEGRITY_CHECK_ENABLED=true
- **THEN** 系统检查 raw_sync_progress 中所有表的同步状态，识别缺口并触发补齐

#### Scenario: 完整性报告包含 raw 表
- **WHEN** 调用 get_sync_summary 获取同步摘要
- **THEN** 摘要中包含 raw 表的完整性信息（总表数、已追平表数、缺口表数）

### Requirement: sync_from_progress 改为 raw 缺口驱动
启动同步 sync_from_progress SHALL 基于 raw_sync_progress 检测缺口，通过统一同步入口补齐数据。

#### Scenario: 启动时检测并补齐 raw 缺口
- **WHEN** 系统启动且存在 raw 表缺口
- **THEN** 系统调用 sync_raw_tables 按优先级补齐缺口（P0 优先，P1-P5 依次）

#### Scenario: 非交易日启动
- **WHEN** 系统在非交易日启动
- **THEN** 系统使用最近交易日作为目标日期检测缺口，不触发无效同步

#### Scenario: 所有 raw 表已追平
- **WHEN** 启动时所有 raw 表的 last_sync_date >= 最近交易日
- **THEN** 系统记录"数据已完整"日志，跳过同步
