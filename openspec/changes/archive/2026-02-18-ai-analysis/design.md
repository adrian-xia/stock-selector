## Context

V1 已实现 AIManager（延迟初始化 GeminiClient、双认证、静默降级）和策略管道 Layer 5 AI 终审。当前 AI 分析结果仅存在于 API 响应中，盘后链路不触发 AI 分析，前端无 AI 结果展示。Prompt 硬编码在 `app/ai/prompts.py` 中。

## Goals / Non-Goals

**Goals:**
- AI 分析结果持久化到数据库，支持历史查询
- 盘后链路自动触发 AI 分析 Top 30 候选股
- Prompt 模板 YAML 化，便于迭代和版本管理
- 前端展示 AI 评分、信号和摘要
- 每日调用上限和 Token 用量记录

**Non-Goals:**
- 不更换 AI 模型（保持 Gemini Flash 单模型）
- 不实现多轮对话或交互式 AI 分析
- 不实现 AI 分析结果的导出功能
- 不做 Prompt A/B 测试框架

## Decisions

### Decision 1: ai_analysis_results 表设计
单表存储，主键 `(ts_code, trade_date)`，包含 ai_score(int)、ai_signal(str)、ai_summary(text)、prompt_version(str)、token_usage(json)、created_at。每日盘后覆盖写入（UPSERT）。

### Decision 2: 盘后链路 AI 步骤位置
放在策略管道之后（步骤 6.5），复用 pipeline_step 的结果。从 ai_analysis_results 读取当日是否已有结果来避免重复调用。失败不阻断，记录错误日志。

### Decision 3: Prompt 模板 YAML 化
在 `app/ai/prompts/` 目录下放置 YAML 文件（如 `stock_analysis_v1.yaml`），包含 system_prompt、user_prompt_template、output_schema。`prompts.py` 改为从 YAML 加载，保留 `build_analysis_prompt()` 接口不变。

### Decision 4: 成本控制
在 AIManager 中增加每日调用计数（基于 Redis key `ai:daily_calls:{date}`），超过 `AI_DAILY_CALL_LIMIT`（默认 5）则跳过。Token 用量记录在 ai_analysis_results.token_usage JSON 字段中。

### Decision 5: 前端展示方案
在选股工作台结果列表中增加 AI 评分列，点击展开显示 AI 摘要。新增 API `GET /api/v1/ai/analysis?date=YYYY-MM-DD` 查询当日 AI 分析结果。

## Risks / Trade-offs

- [Gemini API 调用成本] → 每日调用上限 + 仅分析 Top 30 候选股
- [API 响应延迟] → 盘后异步执行，前端查询已持久化的结果
- [Prompt 迭代风险] → YAML 模板带版本号，结果表记录 prompt_version 便于追溯
