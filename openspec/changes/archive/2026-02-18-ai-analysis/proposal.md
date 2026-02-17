## Why

AIManager 和 GeminiClient 已在 V1 实现并集成到策略管道 Layer 5，但 AI 分析结果仅存在于内存中（随请求结束丢失），盘后链路不包含 AI 步骤，前端无法展示 AI 分析结果。需要补全结果持久化、盘后链路集成、前端展示和成本控制，使 AI 分析成为完整的端到端功能。

## What Changes

- 新增 `ai_analysis_results` 数据库表 + Alembic 迁移，持久化 AI 分析结果
- 新增 AI 结果写入/查询方法到 AIManager
- 盘后链路集成：策略管道后触发 AI 分析 Top 30 候选股，结果写入数据库，失败不阻断
- Prompt 模板从硬编码迁移到 YAML 文件管理（Git 版本控制）
- 新增 API 端点查询 AI 分析结果
- 前端选股工作台展示 AI 分析结果（评分、信号、摘要）
- 成本控制：每日调用上限 + Token 用量记录

## Capabilities

### New Capabilities
- `ai-result-storage`: AI 分析结果持久化存储和查询
- `ai-prompt-yaml`: YAML 格式 Prompt 模板管理

### Modified Capabilities
- `scheduler-jobs`: 盘后链路增加 AI 分析步骤（步骤 6.5，策略管道后、完成前）
- `ai-manager`: AIManager 增加结果写入/查询方法和成本控制

## Impact

- 新增 1 张数据库表 `ai_analysis_results` + Alembic 迁移
- 修改 `app/ai/manager.py`、`app/ai/prompts.py`
- 修改 `app/scheduler/jobs.py`
- 新增 `app/ai/prompts/` YAML 模板目录
- 新增/修改 API 端点 `app/api/strategy.py`
- 修改前端 `web/src/pages/workbench/`
