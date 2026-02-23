## MODIFIED Requirements

### Requirement: batch_insert 统一为 DO UPDATE
batch_insert SHALL 使用 `ON CONFLICT DO UPDATE` 替代 `ON CONFLICT DO NOTHING`，确保数据修正能同步到业务表。

#### Scenario: 重复数据更新
- **WHEN** ETL 写入业务表时遇到主键冲突（数据已存在）
- **THEN** 系统更新已有行的非主键字段为最新值

#### Scenario: 首次写入
- **WHEN** ETL 写入业务表时无主键冲突
- **THEN** 系统正常插入新行

### Requirement: COPY 协议临时表修复
copy_writer SHALL 在执行 COPY 前显式创建临时表，解决 `_tmp_*` 表不存在的问题。

#### Scenario: COPY 协议正常工作
- **WHEN** 批量写入 raw 表或业务表
- **THEN** 系统创建临时表 → COPY 数据到临时表 → UPSERT 到目标表 → 临时表自动清理

#### Scenario: COPY 失败降级
- **WHEN** COPY 协议因非临时表原因失败（如连接异常）
- **THEN** 系统降级到 INSERT 模式，记录 WARNING 日志

### Requirement: P1 财务数据 ETL 补全
etl_pipeline SHALL 补全 P1 财务数据的 ETL 转换函数，覆盖 income、balancesheet、cashflow 等表。

#### Scenario: 利润表 ETL
- **WHEN** raw_tushare_income 有新数据
- **THEN** transform_tushare_income 清洗数据并写入 finance_indicator 相关字段

#### Scenario: 资产负债表 ETL
- **WHEN** raw_tushare_balancesheet 有新数据
- **THEN** transform_tushare_balancesheet 清洗数据并写入对应业务表

#### Scenario: 现金流量表 ETL
- **WHEN** raw_tushare_cashflow 有新数据
- **THEN** transform_tushare_cashflow 清洗数据并写入对应业务表

### Requirement: P3 同步问题修复
etl_pipeline SHALL 修复 P3 指数数据的已知同步问题。

#### Scenario: index_factor_pro 接口处理
- **WHEN** Tushare index_factor_pro 接口返回"请指定正确的接口名"
- **THEN** 系统使用正确的接口名重试，或标记为不可用并跳过

#### Scenario: industry_member null 主键过滤
- **WHEN** raw_tushare_index_member_all 数据中 index_code 为 null
- **THEN** 系统过滤掉 null 主键行后再写入（已在 _upsert_raw 中实现）

#### Scenario: industry_classify 空数据处理
- **WHEN** index_classify 接口返回 0 行数据
- **THEN** 系统记录 WARNING 日志，尝试使用不同参数重新获取
