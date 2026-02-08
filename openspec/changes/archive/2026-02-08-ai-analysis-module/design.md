## Context

策略引擎 Pipeline 已实现 5 层漏斗筛选，其中 Layer 5（AI 终审）当前为直通占位，直接返回 Layer 4 结果。现有代码结构：

- `app/strategy/pipeline.py` 中 `_layer5_ai_placeholder()` 接收 `list[StockPick]` 并原样返回
- `app/config.py` 使用 Pydantic v2 `BaseSettings`，`.env.example` 已预留 `GEMINI_API_KEY`
- API 路由通过 `app.include_router()` 注册，现有 `/api/v1/strategy` 和 `/api/v1/backtest`

V1 约束：仅接 Gemini Flash 单模型，去掉降级状态机/Prompt 版本管理/Token 桶/模型健康检查。调用失败时跳过 AI，日志告警，返回 Layer 4 原始结果。

## Goals / Non-Goals

**Goals:**
- 实现 Gemini Flash 客户端，支持异步调用、JSON 响应解析、超时和重试
- 实现 AIManager 编排器，对候选股票批量分析并输出 AI 评分
- 将 Layer 5 从直通改为调用 AIManager，按 AI 评分重排序
- Prompt 模板硬编码在代码中，支持情感分析和量化信号两种分析任务
- 提供 AI 相关配置项，通过 `.env` 管理
- AI 分析结果通过现有 `/api/v1/strategy/run` 返回，在 StockPick 中附加 AI 字段

**Non-Goals:**
- 不做三模型交叉验证和投票聚合（V2）
- 不做降级状态机和模型健康检查（V2）
- 不做 Prompt 版本管理和 A/B 测试（V2）
- 不做 Token 桶限流和精细成本控制（V2）
- 不新增 AI 相关数据库表（V2 再加 `ai_analysis_results`）
- 不新增独立的 `/api/v1/ai` 路由——AI 分析集成在 Pipeline 内部

## Decisions

### D1: Gemini SDK 选择 — 使用 `google-genai`

使用 Google 官方的 `google-genai` SDK（新版统一 SDK），而非旧版 `google-generativeai`。

**理由：**
- `google-genai` 是 Google 推荐的新版 SDK，同时支持 Gemini API 和 Vertex AI
- 原生支持 async（`client.aio`），与项目 async/await 风格一致
- 支持 `response_mime_type="application/json"` 强制 JSON 输出，减少解析失败

**替代方案：**
- `google-generativeai`（旧版）：不原生支持 async，需要 `asyncio.to_thread` 包装
- 直接调用 REST API：需要自行处理认证、重试、流式响应，工作量大

### D2: AI 分析不独立建 API — 集成在 Pipeline Layer 5

AI 分析不暴露独立的 HTTP 端点，而是作为 Pipeline Layer 5 的内部实现。前端通过 `POST /api/v1/strategy/run` 获取包含 AI 评分的最终结果。

**理由：**
- V1 AI 分析与选股流程强耦合，没有独立调用的场景
- 减少 API 表面积，降低维护成本
- 前端无需额外请求，一次调用获取完整结果

**替代方案：**
- 独立 `/api/v1/ai/analyze` 端点：增加复杂度，前端需要两次请求编排

### D3: AI 评分模型 — 扩展 StockPick dataclass

在 `StockPick` 中新增可选字段 `ai_score`（float | None）和 `ai_summary`（str | None），而非创建新的数据结构。

**理由：**
- 最小改动，保持 Pipeline 数据流一致
- 前端响应自然包含 AI 信息，无需额外映射
- `None` 表示 AI 未执行（配置未开启或调用失败）

### D4: Prompt 策略 — V1 单 Prompt 综合分析

V1 使用单个综合 Prompt，将股票的技术指标、基本面数据和策略匹配信息一起发送给 Gemini，要求返回结构化 JSON 评分。不拆分为情感分析和量化信号两个独立 Prompt。

**理由：**
- V1 不接入新闻数据源，情感分析无输入数据
- 单 Prompt 减少 API 调用次数，降低成本和延迟
- Gemini Flash 上下文窗口足够处理 30 只股票的综合数据

**Prompt 输出格式：**
```json
{
  "analysis": [
    {
      "ts_code": "600519.SH",
      "score": 85,
      "signal": "BUY",
      "reasoning": "均线多头排列，ROE 持续高位..."
    }
  ]
}
```

### D5: 批量 vs 逐只分析 — 批量发送

将 Layer 4 的全部候选股票（最多 30 只）打包在一个 Prompt 中发送，而非逐只调用。

**理由：**
- 30 只股票的上下文数据量约 2000-4000 tokens，远低于 Gemini Flash 的上下文限制
- 单次调用 vs 30 次调用：延迟从 ~30s 降至 ~3s，成本降低 ~90%
- 模型可以在股票间做横向比较，评分更合理

**替代方案：**
- 逐只分析：延迟高、成本高，但每只股票可获得更详细的分析

### D6: 失败处理 — 静默降级

Gemini 调用失败（超时、限流、API 错误）时，Layer 5 记录 warning 日志并返回 Layer 4 原始结果（ai_score 为 None）。不抛异常，不阻断 Pipeline。

**理由：**
- AI 评分是增值功能，不应阻断核心选股流程
- V1 单模型无降级链路，失败即跳过
- 前端通过 `ai_score is None` 判断 AI 是否执行

### D7: AIManager 生命周期 — 模块级延迟初始化

AIManager 在首次调用时延迟初始化（检查 `GEMINI_API_KEY` 是否配置），而非在 FastAPI lifespan 中强制初始化。

**理由：**
- 未配置 API Key 时不应阻止应用启动（AI 是可选功能）
- 避免在 lifespan 中引入额外的初始化逻辑
- 首次调用时初始化，后续复用单例

## Risks / Trade-offs

| 风险 | 缓解措施 |
|:---|:---|
| Gemini API 响应非法 JSON | 使用 `response_mime_type="application/json"` 强制 JSON 输出；解析失败时 fallback 到 Layer 4 结果 |
| 单次批量分析 30 只股票，模型可能遗漏或混淆 | Prompt 中明确要求逐只分析并返回数组；校验返回数量与输入一致 |
| API Key 泄露风险 | Key 仅存在 `.env` 文件中，`.gitignore` 已排除；日志中不打印 Key |
| Gemini Flash 免费额度用尽 | 配置 `AI_DAILY_BUDGET_USD` 上限，超出后跳过 AI；V1 靠漏斗筛选控制调用量（每日最多 1 次 Pipeline） |
| 批量 Prompt 输出格式不稳定 | 定义严格的 JSON Schema 约束；Pydantic 模型校验响应；校验失败时降级 |
