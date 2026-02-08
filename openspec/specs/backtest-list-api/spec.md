## ADDED Requirements

### Requirement: 回测任务列表接口
系统 SHALL 提供 `GET /api/v1/backtest/list` 接口，从 `backtest_tasks` 表分页查询回测任务，按创建时间倒序排列。支持 `page`（默认 1）和 `page_size`（默认 20，最大 100）参数。

#### Scenario: 查询第一页
- **WHEN** 请求 `GET /api/v1/backtest/list`
- **THEN** 返回最近 20 条回测任务，按创建时间倒序

#### Scenario: 分页查询
- **WHEN** 请求 `GET /api/v1/backtest/list?page=2&page_size=10`
- **THEN** 返回第 11-20 条记录

#### Scenario: 无回测任务
- **WHEN** 数据库中没有回测任务
- **THEN** 返回空列表，total 为 0

### Requirement: 回测列表响应格式
系统 SHALL 返回以下 JSON 格式：`{ "total": 50, "page": 1, "page_size": 20, "items": [{ "task_id": 1, "strategy_name": "ma_cross", "stock_count": 3, "start_date": "2024-01-01", "end_date": "2025-12-31", "status": "completed", "annual_return": 0.1342, "created_at": "2026-02-08T10:30:00" }] }`。

#### Scenario: 列表项包含绩效摘要
- **WHEN** 回测任务状态为 completed
- **THEN** 列表项包含 annual_return 字段（从 backtest_results 表 JOIN 查询）

#### Scenario: 未完成任务无绩效数据
- **WHEN** 回测任务状态为 pending/running/failed
- **THEN** annual_return 字段为 null
