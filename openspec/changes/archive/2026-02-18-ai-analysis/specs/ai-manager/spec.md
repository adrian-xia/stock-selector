## MODIFIED Requirements

### Requirement: AIManager 结果写入与成本控制
AIManager SHALL 增加结果持久化写入方法和每日调用上限控制。

#### Scenario: 写入分析结果到数据库
- **WHEN** AI 分析完成后调用 `save_results(picks, trade_date)`
- **THEN** 将分析结果 UPSERT 到 ai_analysis_results 表

#### Scenario: 每日调用上限
- **WHEN** 当日 AI 调用次数已达到 `AI_DAILY_CALL_LIMIT`（默认 5）
- **THEN** 跳过 AI 分析，记录日志，返回原始 picks

#### Scenario: Token 用量记录
- **WHEN** AI 分析完成
- **THEN** 将 prompt_tokens、completion_tokens、total_tokens 记录到 ai_analysis_results.token_usage

#### Scenario: 查询当日结果
- **WHEN** 调用 `get_results(trade_date)`
- **THEN** 返回当日所有 AI 分析结果列表
