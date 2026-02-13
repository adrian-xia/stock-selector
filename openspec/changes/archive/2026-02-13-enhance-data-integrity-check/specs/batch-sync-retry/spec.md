## MODIFIED Requirements

### Requirement: 系统应自动重试失败的股票同步

系统 SHALL 在批量同步完成后，自动重试失败的股票，最多重试指定次数（默认 2 次）。每批数据拉取和写入在事务中完成。

#### Scenario: 重试失败的股票
- **WHEN** 批量同步 100 只股票，其中 10 只失败
- **THEN** 系统自动重试这 10 只失败的股票

#### Scenario: 达到最大重试次数后标记 failed
- **WHEN** 某股票重试 2 次后仍然失败
- **THEN** 系统将该股票的 status 标记为 'failed'，记录 error_message

#### Scenario: 单批失败事务回滚
- **WHEN** 某批次数据写入过程中发生错误
- **THEN** 该批次的事务回滚（日线数据写入和 data_date 更新均不生效），已完成的批次不受影响

### Requirement: 系统应在重试时降低并发数

系统 SHALL 在重试失败的股票时，降低并发数以避免再次触发 API 限流。

#### Scenario: 重试时降低并发数
- **WHEN** 第一次同步使用并发数 10，部分股票失败
- **THEN** 系统重试时使用并发数 4（降低并发）

### Requirement: 系统应记录重试统计信息

系统 SHALL 记录每次重试的统计信息，包括重试次数、成功数、失败数。

#### Scenario: 记录重试统计信息
- **WHEN** 系统进行第 1 次重试，10 只股票中 6 只成功
- **THEN** 系统记录日志：重试第 1/2 次，10 只股票，成功 6 只

#### Scenario: 记录失败股票的错误信息
- **WHEN** 某股票重试后仍然失败，错误信息为 "API timeout"
- **THEN** 系统更新 stock_sync_progress 表的 error_message 字段
