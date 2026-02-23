## ADDED Requirements

### Requirement: raw_sync_progress 进度追踪表
系统 SHALL 维护 `raw_sync_progress` 表，记录每张 raw 表的同步进度（表名、最新同步日期、同步行数、更新时间）。

#### Scenario: 同步完成后更新进度
- **WHEN** 某张 raw 表完成一次同步写入
- **THEN** 系统更新 raw_sync_progress 中该表的 last_sync_date 和 last_sync_rows

#### Scenario: 新 raw 表首次同步
- **WHEN** raw_sync_progress 中不存在某张 raw 表的记录
- **THEN** 系统插入新记录，last_sync_date 设为同步的最早日期

### Requirement: raw 表缺口检测
系统 SHALL 能够检测每张日频 raw 表相对于交易日历的数据缺口，识别缺失的交易日。

#### Scenario: 检测到缺口
- **WHEN** raw_tushare_daily 的 last_sync_date 为 2026-02-10，而最新交易日为 2026-02-13
- **THEN** 系统识别出 2026-02-11、2026-02-12、2026-02-13 为缺口日期

#### Scenario: 无缺口
- **WHEN** raw 表的 last_sync_date 等于最新交易日
- **THEN** 系统报告该表无缺口，跳过同步

#### Scenario: 非日频表缺口检测
- **WHEN** 检测周频表（如 raw_tushare_weekly）的缺口
- **THEN** 系统按周频率检测，仅在每周五的交易日检查

### Requirement: 自动补齐缺口
系统 SHALL 在检测到缺口后，自动调用对应的 sync_raw_* 方法补齐缺失数据，并更新 raw_sync_progress。

#### Scenario: 启动时补齐
- **WHEN** 系统启动且 raw 表存在缺口
- **THEN** 系统按 P0 → P1 → P2 → P3 → P4 → P5 顺序补齐缺口数据

#### Scenario: 补齐失败不阻断
- **WHEN** 某张 raw 表补齐失败（如 API 不可用）
- **THEN** 系统记录错误日志，继续补齐其他表，不阻断启动流程

#### Scenario: 断点续传
- **WHEN** 补齐过程中断（如进程重启）
- **THEN** 下次启动时从 raw_sync_progress 记录的位置继续，不重复已完成的同步
