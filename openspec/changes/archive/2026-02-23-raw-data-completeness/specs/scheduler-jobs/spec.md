## MODIFIED Requirements

### Requirement: 盘后链路增加 P1 财务数据步骤
盘后链路 SHALL 在步骤 3.5 之前增加 P1 财务数据同步步骤，按季度同步财务报表数据。

#### Scenario: 季报期自动同步
- **WHEN** 盘后链路执行且当前处于季报披露期（每年 1-4 月、7-8 月、10 月）
- **THEN** 系统调用 sync_raw_fina 同步最新季度的财务数据，再 ETL 到业务表

#### Scenario: 非季报期跳过
- **WHEN** 盘后链路执行且不在季报披露期
- **THEN** 系统跳过 P1 财务数据同步，记录日志

### Requirement: 盘后链路 raw 追平检查
盘后链路 SHALL 在 P2-P5 同步完成后执行 raw 追平检查，确保所有 raw 表追到目标日期。

#### Scenario: 发现未追平的 raw 表
- **WHEN** 盘后链路完成 P2-P5 同步后，raw_sync_progress 中某些表的 last_sync_date < 目标日期
- **THEN** 系统自动补同步未追平的表

#### Scenario: 全部已追平
- **WHEN** 所有 raw 表的 last_sync_date >= 目标日期
- **THEN** 系统记录"raw 表全部追平"日志，继续后续步骤

### Requirement: 盘后链路补全 P4 成分股和技术指标
盘后链路 SHALL 在板块数据同步步骤中包含 concept_member 同步和 concept_technical_daily 计算。

#### Scenario: 板块成分股同步
- **WHEN** 盘后链路执行步骤 3.7
- **THEN** 系统同步板块日线行情后，还同步板块成分股（sync_concept_member）

#### Scenario: 板块技术指标计算
- **WHEN** concept_daily 数据同步完成
- **THEN** 系统计算板块技术指标写入 concept_technical_daily

### Requirement: P5 同步失败项修复
盘后链路 SHALL 修复 P5 中因代码 bug 导致的同步失败项，对于 VIP 接口限制的项记录日志跳过。

#### Scenario: 代码 bug 修复后同步成功
- **WHEN** 修复参数错误、列名不匹配等代码 bug 后执行 P5 同步
- **THEN** 之前失败的项（如 daily_share、hm_board 等）能够正常同步

#### Scenario: VIP 接口不可用
- **WHEN** 某个 P5 接口需要 VIP 权限且当前 token 无权限
- **THEN** 系统记录 WARNING 日志并跳过该项，不阻断其他同步
