## MODIFIED Requirements

### Requirement: technical_daily table schema
The `technical_daily` table SHALL contain the following additional columns beyond the existing 23 indicator columns:

- `wr`: Numeric(10,4), nullable — Williams %R (14-period)
- `cci`: Numeric(10,4), nullable — CCI (14-period)
- `bias`: Numeric(10,4), nullable — BIAS based on MA20
- `obv`: Numeric(20,2), nullable — On-Balance Volume (cumulative)
- `donchian_upper`: Numeric(10,2), nullable — Donchian channel upper band (20-period)
- `donchian_lower`: Numeric(10,2), nullable — Donchian channel lower band (20-period)

All new columns SHALL be nullable with default NULL to maintain backward compatibility.

#### Scenario: New columns exist after migration
- **WHEN** `alembic upgrade head` is executed
- **THEN** the `technical_daily` table SHALL have columns `wr`, `cci`, `bias`, `obv`, `donchian_upper`, `donchian_lower`

#### Scenario: Existing data unaffected
- **WHEN** migration runs on a table with existing data
- **THEN** all existing rows SHALL have NULL values for the 6 new columns

## ADDED Requirements

### Requirement: TimescaleDB 超表支持
database-schema SHALL 支持将 `stock_daily` 和 `technical_daily` 表转换为 TimescaleDB 超表。转换通过 Alembic 迁移脚本执行，TimescaleDB 为可选依赖。

#### Scenario: TimescaleDB 可用时创建超表
- **WHEN** 执行迁移且 TimescaleDB 扩展已安装
- **THEN** stock_daily 和 technical_daily SHALL 被转换为超表
- **AND** 分区维度为 trade_date，chunk 间隔 1 个月

#### Scenario: TimescaleDB 不可用时保持普通表
- **WHEN** 执行迁移且 TimescaleDB 未安装
- **THEN** stock_daily 和 technical_daily SHALL 保持为普通表
- **AND** 所有功能 SHALL 正常工作

### Requirement: raw 表复合索引
所有 P0-P5 raw 表 SHALL 补充 `(ts_code, trade_date)` 复合索引（对于以 ts_code 和日期字段为主键的表），优化 ETL 阶段的查询性能。

#### Scenario: 迁移后 raw 表索引存在
- **WHEN** 执行 `alembic upgrade head`
- **THEN** raw_tushare_daily、raw_tushare_adj_factor、raw_tushare_daily_basic 等 raw 表 SHALL 拥有 `(ts_code, trade_date)` 复合索引

#### Scenario: 索引提升 ETL 查询性能
- **WHEN** ETL 阶段执行 `SELECT * FROM raw_tushare_daily WHERE trade_date = :date`
- **THEN** 查询 SHALL 使用 trade_date 索引（已有），按 ts_code 排序时可利用复合索引
