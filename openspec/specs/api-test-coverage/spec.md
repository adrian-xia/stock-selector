## ADDED Requirements

### Requirement: 策略 API 端点测试覆盖
系统 SHALL 为策略 API 的全部 3 个端点提供单元测试，覆盖正常路径和错误路径。

#### Scenario: POST /strategy/run 正常执行
- **WHEN** 调用 run_strategy 传入有效策略名称列表
- **THEN** 返回 StrategyRunResponse，包含 target_date、total_picks、picks 列表

#### Scenario: POST /strategy/run 无效策略名称
- **WHEN** 调用 run_strategy 传入不存在的策略名称
- **THEN** 抛出 HTTPException 400，detail 包含无效策略名称

#### Scenario: GET /strategy/list 返回全部策略
- **WHEN** 调用 list_strategies 不传 category 参数
- **THEN** 返回包含所有已注册策略的 StrategyListResponse

#### Scenario: GET /strategy/list 按分类过滤
- **WHEN** 调用 list_strategies 传入 category="technical"
- **THEN** 仅返回技术面策略

#### Scenario: GET /strategy/schema 查询存在的策略
- **WHEN** 调用 get_strategy_schema 传入已注册的策略名称
- **THEN** 返回 StrategySchemaResponse，包含 name、display_name、default_params

#### Scenario: GET /strategy/schema 查询不存在的策略
- **WHEN** 调用 get_strategy_schema 传入不存在的策略名称
- **THEN** 抛出 HTTPException 404

### Requirement: 回测执行端点测试覆盖
系统 SHALL 为回测 API 的 run 和 result 端点提供单元测试。

#### Scenario: POST /backtest/run 正常执行
- **WHEN** 调用 run_backtest_api 传入有效参数
- **THEN** 创建 task 记录，执行回测，返回 BacktestRunResponse（status="completed"）

#### Scenario: POST /backtest/run 日期范围无效
- **WHEN** 调用 run_backtest_api 且 start_date >= end_date
- **THEN** 抛出 HTTPException 400

#### Scenario: POST /backtest/run 回测执行失败
- **WHEN** 调用 run_backtest_api 且回测引擎抛出异常
- **THEN** 返回 BacktestRunResponse（status="failed"，error_message 包含错误信息）

#### Scenario: GET /backtest/result 查询已完成任务
- **WHEN** 调用 get_backtest_result 传入已完成任务的 task_id
- **THEN** 返回完整的 BacktestResultResponse，包含 metrics、trades、equity_curve

#### Scenario: GET /backtest/result 查询不存在的任务
- **WHEN** 调用 get_backtest_result 传入不存在的 task_id
- **THEN** 抛出 HTTPException 404

#### Scenario: GET /backtest/result 查询运行中的任务
- **WHEN** 调用 get_backtest_result 传入 status="running" 的 task_id
- **THEN** 返回 BacktestResultResponse（status="running"，result 为 None）

#### Scenario: GET /backtest/result 查询失败的任务
- **WHEN** 调用 get_backtest_result 传入 status="failed" 的 task_id
- **THEN** 返回 BacktestResultResponse（status="failed"，包含 error_message）
