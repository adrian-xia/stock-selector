## MODIFIED Requirements

### Requirement: 数据初始化流程
数据初始化脚本 SHALL 以 raw 表为驱动，调用统一同步入口 `sync_raw_tables` 完成全量数据初始化，不再有独立的业务表写入逻辑。

#### Scenario: 首次初始化
- **WHEN** 用户运行 `python -m scripts.init_data` 并选择日期范围
- **THEN** 系统按 P0 → P1 → P2 → P3 → P4 → P5 顺序调用 `sync_raw_tables(group, start, end, mode="full")`，先写 raw 表再 ETL 到业务表

#### Scenario: 中断后恢复
- **WHEN** 初始化过程中断后重新运行
- **THEN** 系统通过 raw_sync_progress 检测已完成的部分，仅补齐缺口数据

#### Scenario: 指标计算
- **WHEN** 所有 raw 表和业务表同步完成
- **THEN** 系统执行全量技术指标计算（compute_all_stocks）
