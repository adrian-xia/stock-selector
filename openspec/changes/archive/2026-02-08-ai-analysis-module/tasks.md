## 1. 依赖与配置

- [x] 1.1 在 `pyproject.toml` 中添加 `google-genai` 依赖
- [x] 1.2 在 `app/config.py` 的 `Settings` 类中添加 Gemini 配置字段（`gemini_api_key`、`gemini_model_id`、`gemini_max_tokens`、`gemini_timeout`、`gemini_max_retries`、`ai_daily_budget_usd`）
- [x] 1.3 更新 `.env.example` 添加 AI 相关配置项及注释

## 2. Gemini 客户端

- [x] 2.1 创建 `app/ai/__init__.py` 和 `app/ai/clients/__init__.py` 模块结构
- [x] 2.2 实现 `app/ai/clients/gemini.py`：自定义异常类（`GeminiError`、`GeminiTimeoutError`、`GeminiAPIError`、`GeminiResponseParseError`）
- [x] 2.3 实现 `GeminiClient` 类：构造函数、`chat()` 异步方法（含超时和重试）、`chat_json()` 方法、`get_last_usage()` 方法

## 3. Prompt 模板与数据模型

- [x] 3.1 实现 `app/ai/schemas.py`：`AIAnalysisItem` 和 `AIAnalysisResponse` Pydantic 模型
- [x] 3.2 实现 `app/ai/prompts.py`：`build_analysis_prompt()` 函数，构建批量股票综合分析 Prompt

## 4. AI 管理器

- [x] 4.1 实现 `app/ai/manager.py`：`AIManager` 类（构造函数、`is_enabled` 属性、`analyze()` 异步方法）
- [x] 4.2 实现 `get_ai_manager()` 单例函数
- [x] 4.3 实现失败降级逻辑：Gemini 调用异常时 warning 日志 + 返回原始 picks
- [x] 4.4 实现部分响应处理：AI 返回数量不匹配时的合并逻辑

## 5. Pipeline 集成

- [x] 5.1 扩展 `StockPick` dataclass：添加 `ai_score`、`ai_signal`、`ai_summary` 可选字段
- [x] 5.2 扩展 `PipelineResult` dataclass：添加 `ai_enabled` 字段
- [x] 5.3 将 `_layer5_ai_placeholder()` 重构为 `_layer5_ai_analysis()`，调用 AIManager 并传入 market_snapshot 和 target_date
- [x] 5.4 更新 `execute_pipeline()` 调用 Layer 5 时传入所需参数，并设置 `ai_enabled` 状态

## 6. API 响应扩展

- [x] 6.1 更新 `app/api/strategy.py` 的响应模型，在 pick 对象中包含 `ai_score`、`ai_signal`、`ai_summary` 字段
- [x] 6.2 在策略执行响应中添加 `ai_enabled` 顶层字段

## 7. 测试

- [x] 7.1 编写 `tests/unit/test_gemini_client.py`：测试 GeminiClient 初始化、异常处理（mock API 调用）
- [x] 7.2 编写 `tests/unit/test_ai_prompts.py`：测试 `build_analysis_prompt()` 输出格式和边界情况
- [x] 7.3 编写 `tests/unit/test_ai_schemas.py`：测试 `AIAnalysisItem` 和 `AIAnalysisResponse` 校验
- [x] 7.4 编写 `tests/unit/test_ai_manager.py`：测试 AIManager 的 analyze 方法（mock GeminiClient）、失败降级、部分响应处理
- [x] 7.5 编写 `tests/unit/test_pipeline_layer5.py`：测试 Layer 5 AI 集成（mock AIManager）
