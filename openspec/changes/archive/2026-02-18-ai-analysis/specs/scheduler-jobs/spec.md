## MODIFIED Requirements

### Requirement: 盘后链路增加 AI 分析步骤
run_post_market_chain SHALL 在策略管道执行后增加 AI 分析步骤（步骤 6.5），对 Top 30 候选股进行 AI 分析并持久化结果。AI 分析失败不阻断后续链路。

#### Scenario: 盘后 AI 分析执行
- **WHEN** 策略管道执行完成且产出候选股
- **THEN** 取 Top 30 候选股调用 AI 分析，结果写入 ai_analysis_results 表

#### Scenario: AI 分析失败不阻断
- **WHEN** AI 分析步骤抛出异常
- **THEN** 记录错误日志，盘后链路继续完成

#### Scenario: 无候选股时跳过
- **WHEN** 策略管道未产出候选股
- **THEN** 跳过 AI 分析步骤，记录日志
