## 1. 数据库模型与迁移

- [x] 1.1 创建 `app/models/ai.py`，定义 AIAnalysisResult ORM 模型（ts_code, trade_date, ai_score, ai_signal, ai_summary, prompt_version, token_usage, created_at）
- [x] 1.2 生成 Alembic 迁移脚本创建 ai_analysis_results 表

## 2. YAML Prompt 模板

- [x] 2.1 创建 `app/ai/prompts/stock_analysis_v1.yaml` 模板文件（version, system_prompt, user_prompt_template, output_schema）
- [x] 2.2 修改 `app/ai/prompts.py`，从 YAML 文件加载模板，保留 `build_analysis_prompt()` 接口

## 3. AIManager 增强

- [x] 3.1 AIManager 增加 `save_results(picks, trade_date, token_usage)` 方法
- [x] 3.2 AIManager 增加 `get_results(trade_date)` 方法
- [x] 3.3 AIManager 增加每日调用上限控制
- [x] 3.4 `analyze()` 方法集成 token_usage 记录和 prompt_version 传递

## 4. 盘后链路集成

- [x] 4.1 修改 `app/scheduler/jobs.py`，在策略管道后增加 AI 分析步骤（步骤 6.5），取 Top 30 候选股，失败不阻断

## 5. API 端点

- [x] 5.1 新增 `GET /api/v1/ai/analysis` 端点，支持按日期查询 AI 分析结果

## 6. 前端展示

- [x] 6.1 新增 AI 分析结果 API 请求函数和 TypeScript 类型定义
- [x] 6.2 选股工作台结果列表增加 AI 评分列，点击展开显示 AI 摘要

## 7. 配置与文档

- [x] 7.1 `.env.example` 增加 `AI_DAILY_CALL_LIMIT` 配置项
- [x] 7.2 更新 README.md、CLAUDE.md、PROJECT_TASKS.md
