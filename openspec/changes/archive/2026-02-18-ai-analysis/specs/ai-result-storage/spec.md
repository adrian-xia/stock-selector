## ADDED Requirements

### Requirement: AI 分析结果持久化
系统 SHALL 提供 `ai_analysis_results` 数据库表，存储每日 AI 分析结果，支持按日期查询。

#### Scenario: 写入 AI 分析结果
- **WHEN** 盘后 AI 分析完成，产出 N 只股票的评分
- **THEN** 系统 SHALL 将结果 UPSERT 到 ai_analysis_results 表，主键为 (ts_code, trade_date)

#### Scenario: 查询 AI 分析结果
- **WHEN** 调用 `GET /api/v1/ai/analysis?date=2026-02-17`
- **THEN** 返回当日所有 AI 分析结果列表，包含 ts_code、ai_score、ai_signal、ai_summary

#### Scenario: 历史结果不被覆盖
- **WHEN** 查询历史日期的 AI 分析结果
- **THEN** 返回该日期的完整分析结果，不受后续日期分析影响

### Requirement: AI 分析结果表结构
ai_analysis_results 表 SHALL 包含以下字段：ts_code(str)、trade_date(date)、ai_score(int, 1-100)、ai_signal(str, buy/hold/sell)、ai_summary(text)、prompt_version(str)、token_usage(json)、created_at(datetime)。主键为 (ts_code, trade_date)。

#### Scenario: 表结构完整
- **WHEN** 执行 Alembic 迁移
- **THEN** ai_analysis_results 表 SHALL 包含所有指定字段和主键约束
