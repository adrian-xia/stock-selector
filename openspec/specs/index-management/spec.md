## ADDED Requirements

### Requirement: 删除非主键索引
系统 SHALL 提供 `drop_indexes(engine, table_name)` 异步函数，删除指定表的所有非主键索引，返回被删除索引的定义列表（用于后续重建）。

#### Scenario: 删除表的非主键索引
- **WHEN** 调用 `drop_indexes(engine, "stock_daily")`
- **THEN** SHALL 删除 idx_stock_daily_code_date、idx_stock_daily_trade_date 等非主键索引
- **AND** SHALL 保留主键约束索引
- **AND** SHALL 返回被删除索引的完整定义（名称、列、类型）

#### Scenario: 表无非主键索引
- **WHEN** 调用 `drop_indexes(engine, table_name)` 且表只有主键索引
- **THEN** SHALL 返回空列表，不执行任何操作

### Requirement: 重建索引
系统 SHALL 提供 `rebuild_indexes(engine, index_definitions)` 异步函数，根据索引定义列表重建索引，使用 `CREATE INDEX CONCURRENTLY` 避免锁表。

#### Scenario: 重建索引成功
- **WHEN** 调用 `rebuild_indexes(engine, index_defs)`
- **THEN** SHALL 使用 CREATE INDEX CONCURRENTLY 逐个重建索引
- **AND** SHALL 记录每个索引的重建耗时

#### Scenario: 重建索引失败
- **WHEN** 某个索引重建失败
- **THEN** SHALL 记录 ERROR 日志（索引名、失败原因）
- **AND** SHALL 继续重建剩余索引，不中断流程
- **AND** SHALL 返回失败索引列表

### Requirement: 全量导入索引管理包装器
系统 SHALL 提供 `with_index_management(engine, table_names)` 异步上下文管理器，在进入时删除指定表的索引，退出时重建。

#### Scenario: 全量导入流程
- **WHEN** 使用 `async with with_index_management(engine, ["stock_daily", "technical_daily"]):`
- **THEN** 进入时 SHALL 删除这些表的非主键索引
- **AND** 退出时 SHALL 重建所有被删除的索引
- **AND** SHALL 记录索引管理的总耗时

#### Scenario: 导入异常时仍重建索引
- **WHEN** 上下文管理器内部发生异常
- **THEN** SHALL 仍然在 finally 中重建索引
- **AND** SHALL 重新抛出原始异常
