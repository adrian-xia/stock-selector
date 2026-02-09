## ADDED Requirements

### Requirement: 轻量级数据嗅探

系统 SHALL 提供轻量级数据嗅探功能，通过查询少量样本股票来检测指定日期的数据是否就绪。

#### Scenario: 数据已就绪

- **WHEN** 查询 5 只样本股票的指定日期数据
- **AND** 其中 4 只（80%）有数据
- **THEN** 返回 True，表示数据已就绪

#### Scenario: 数据未就绪

- **WHEN** 查询 5 只样本股票的指定日期数据
- **AND** 其中只有 2 只（40%）有数据
- **THEN** 返回 False，表示数据未就绪

#### Scenario: 无任何数据

- **WHEN** 查询 5 只样本股票的指定日期数据
- **AND** 所有样本股票都没有数据
- **THEN** 返回 False，表示数据未就绪

### Requirement: 样本股票配置

系统 SHALL 支持配置样本股票列表和成功阈值。

#### Scenario: 使用默认样本股票

- **WHEN** 未配置样本股票列表
- **THEN** 使用默认的 5 只大盘股（茅台、平安银行等）

#### Scenario: 使用自定义样本股票

- **WHEN** 配置了自定义样本股票列表
- **THEN** 使用配置的股票列表进行嗅探

#### Scenario: 使用自定义阈值

- **WHEN** 配置了成功阈值为 0.9（90%）
- **AND** 查询 10 只样本股票，其中 9 只有数据
- **THEN** 返回 True，表示数据已就绪

### Requirement: 性能要求

数据嗅探 SHALL 在 100 毫秒内完成。

#### Scenario: 快速嗅探

- **WHEN** 执行数据嗅探
- **THEN** 查询耗时小于 100 毫秒

#### Scenario: 使用索引查询

- **WHEN** 执行数据嗅探
- **THEN** 使用 `idx_stock_daily_code_date` 索引进行查询
