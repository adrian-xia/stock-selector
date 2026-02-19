## MODIFIED Requirements

### Requirement: 系统应在启动时更新股票列表

系统 SHALL 在启动时数据完整性检查之前，自动更新股票列表，确保使用最新的股票基本信息（包括上市日期、退市日期）。

#### Scenario: 启动时自动更新股票列表
- **WHEN** 系统启动
- **THEN** 系统在初始化进度表之前，自动调用 Tushare 更新股票列表

#### Scenario: 更新股票列表失败不阻断启动
- **WHEN** 启动时更新股票列表失败（Tushare API 不可用）
- **THEN** 系统记录警告日志，使用数据库中的旧数据继续启动

#### Scenario: 可配置是否启动时更新股票列表
- **WHEN** 系统配置 SYNC_STOCK_LIST_ON_STARTUP=false
- **THEN** 系统跳过启动时更新股票列表，直接使用数据库中的数据

### Requirement: 系统应基于进度表检测数据完整性

系统 SHALL 通过 `stock_sync_progress` 表的 `data_date` 和 `indicator_date` 字段判断数据完整性，排除 `status='delisted'` 的股票后计算完成率。

#### Scenario: 检测需要同步的股票
- **WHEN** 目标日期为 2026-02-12，有 500 只非 delisted 股票的 data_date < 2026-02-12
- **THEN** 系统识别这 500 只股票需要同步数据

#### Scenario: 新股自动识别
- **WHEN** 新股加入进度表，data_date 为默认值 1900-01-01
- **THEN** 系统识别该股票需要从 data_start_date 开始同步全部历史数据

#### Scenario: 完成率计算（排除 delisted）
- **WHEN** 8000 只股票中 1000 只为 delisted，剩余 7000 只中 6650 只的 data_date >= target_date 且 indicator_date >= target_date
- **THEN** 系统计算完成率为 6650/7000 = 95%

### Requirement: 系统应在计算预期股票数时排除退市股票

系统 SHALL 通过 `stock_sync_progress.status` 字段排除已退市股票，无需 JOIN stocks 表。

#### Scenario: 排除 delisted 状态的股票
- **WHEN** 初始化进度表后，有 1058 只股票被标记为 status='delisted'
- **THEN** 系统在查询待同步股票和计算完成率时自动排除这些股票

#### Scenario: 退市状态通过事务同步
- **WHEN** stocks 表中有新退市的股票
- **THEN** 系统在事务中同时更新 stocks 表和 progress 表，保证状态一致
