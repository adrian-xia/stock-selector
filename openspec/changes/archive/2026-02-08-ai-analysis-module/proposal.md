## Why

策略引擎 Pipeline 的 Layer 5（AI 层）目前是直通占位，候选股票未经 AI 分析直接输出。V1 需要接入 Gemini Flash 单模型，对策略筛选出的候选股票进行智能分析（新闻情感 + 量化信号验证），输出 AI 评分和投资建议，提升选股质量。

## What Changes

- 新增 Gemini Flash 客户端，封装 API 调用、重试、超时处理
- 新增 Prompt 模板管理，支持情感分析和量化信号两种分析任务
- 新增 AI 分析管理器（AIManager），编排分析流程：接收候选股票 → 构建上下文 → 调用 Gemini → 解析结果 → 输出评分
- 将 Pipeline Layer 5 从直通改为调用 AIManager 进行 AI 评分和排序
- 新增 AI 分析相关的 HTTP API（提交分析、查询结果）
- 新增 AI 相关配置项（API Key、模型 ID、超时、每日预算等）

## Capabilities

### New Capabilities
- `gemini-client`: Gemini Flash API 客户端，封装聊天调用、JSON 解析、重试和错误处理
- `ai-prompt-templates`: Prompt 模板管理，包含情感分析和量化信号验证两种模板，支持上下文变量渲染
- `ai-manager`: AI 分析编排器，接收候选股票列表，调用 Gemini 进行分析，聚合评分，输出最终排序结果
- `ai-api`: AI 分析相关的 HTTP API 端点（触发分析、查询结果）

### Modified Capabilities
- `strategy-pipeline`: Layer 5 从直通改为调用 AIManager 进行 AI 分析和重排序
- `app-config`: 新增 Gemini API 相关配置项（API Key、模型 ID、超时、每日预算限制）

## Impact

- **新增代码：** `app/ai/` 目录（clients/gemini.py、prompts/、manager.py）
- **修改代码：** `app/strategy/pipeline.py`（Layer 5 集成）、`app/config.py`（新增配置项）
- **新增 API：** `app/api/ai.py`（POST /api/v1/ai/analyze、GET /api/v1/ai/result/{task_id}）
- **依赖新增：** `google-genai`（Gemini Python SDK）
- **配置新增：** `.env` 中增加 `GEMINI_API_KEY`、`GEMINI_MODEL_ID`、`AI_DAILY_BUDGET_USD` 等
- **数据库：** V1 不新增 AI 相关表，分析结果通过 API 返回，不持久化（V2 再加 `ai_analysis_results` 表）
