## MODIFIED Requirements

### Requirement: Tushare ETL 清洗函数集
etl.py SHALL 提供完整的 Tushare 数据清洗函数集（transform_tushare_stock_basic, transform_tushare_trade_cal, transform_tushare_daily, transform_tushare_fina_indicator, transform_tushare_moneyflow, transform_tushare_top_list, transform_tushare_top_inst, transform_tushare_index_basic, transform_tushare_index_daily, transform_tushare_index_weight, transform_tushare_industry_classify, transform_tushare_industry_member, transform_tushare_index_technical），替代原有的 clean_baostock_* / clean_akshare_* 函数。

#### Scenario: 导入新的清洗函数
- **WHEN** 从 etl.py 导入清洗函数
- **THEN** transform_tushare_* 系列函数全部可用，clean_baostock_* / clean_akshare_* 已移除

## ADDED Requirements

### Requirement: batch_insert 支持 COPY 协议
`batch_insert()` 函数 SHALL 优先使用 COPY 协议写入（通过 `copy_insert()`），失败时自动降级到原有 `pg_insert().values()` 方式。新增 `use_copy` 参数控制是否启用 COPY 协议（默认 True）。

#### Scenario: 默认使用 COPY 协议写入
- **WHEN** 调用 `batch_insert(session, table, rows)` 且未指定 use_copy
- **THEN** SHALL 优先使用 `copy_insert()` 写入
- **AND** 写入成功时 SHALL 记录 COPY 协议写入日志

#### Scenario: COPY 失败降级到 INSERT
- **WHEN** 调用 `batch_insert(session, table, rows)` 且 COPY 写入失败
- **THEN** SHALL 自动降级到原有 `pg_insert().values().on_conflict_do_nothing()` 方式
- **AND** SHALL 记录 WARNING 日志说明降级

#### Scenario: 显式禁用 COPY 协议
- **WHEN** 调用 `batch_insert(session, table, rows, use_copy=False)`
- **THEN** SHALL 直接使用原有 `pg_insert().values()` 方式，不尝试 COPY

### Requirement: _upsert_raw 支持 COPY 协议
`_upsert_raw()` 方法 SHALL 优先使用 COPY 协议写入（通过 `copy_insert(conflict="update")`），失败时自动降级到原有方式。

#### Scenario: raw 表默认使用 COPY 协议
- **WHEN** 调用 `_upsert_raw(session, table, rows)`
- **THEN** SHALL 优先使用 `copy_insert(conflict="update")` 写入
- **AND** 冲突时 SHALL 更新已有行

#### Scenario: COPY 失败降级
- **WHEN** COPY 写入 raw 表失败
- **THEN** SHALL 降级到原有 `pg_insert().on_conflict_do_update()` 方式
