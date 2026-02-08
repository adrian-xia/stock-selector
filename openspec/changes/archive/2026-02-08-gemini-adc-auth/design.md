## Context

当前 `GeminiClient` 仅支持 API Key 认证，构造时必须传入非空 `api_key`。用户持有 Google AI Pro 账号，希望通过 Google Application Default Credentials (ADC) 调用 Gemini API，无需手动管理密钥。

涉及文件：
- `app/ai/clients/gemini.py` — 客户端初始化
- `app/config.py` — 配置加载
- `app/ai/manager.py` — 启用判断与客户端创建

## Goals / Non-Goals

**Goals:**
- GeminiClient 支持 ADC 认证方式，与 API Key 二选一
- 配置层新增 `GEMINI_USE_ADC` 开关
- AIManager 正确识别 ADC 模式并启用 AI 分析
- 向后兼容：现有 API Key 用户无需改动

**Non-Goals:**
- 不实现 Service Account JSON 文件路径配置（ADC 机制已覆盖）
- 不实现运行时切换认证方式（重启生效即可）
- 不修改 Gemini API 调用逻辑（chat/chat_json 不变）

## Decisions

### D1: 认证优先级 — API Key 优先于 ADC

**选择：** 当 `api_key` 非空时使用 API Key，忽略 `use_adc` 设置。

**理由：** API Key 是显式配置，语义更明确。避免两者同时配置时的歧义。

**替代方案：** 两者互斥、配置冲突时报错 → 增加配置复杂度，对用户不友好。

### D2: 使用 `google.auth.default()` 获取凭据

**选择：** 调用 `google.auth.default()` 获取 credentials，传给 `genai.Client(credentials=creds)`。

**理由：** 这是 Google 官方推荐的 ADC 方式，自动支持：
- 本地开发：`gcloud auth application-default login`
- 服务器：Service Account / Workload Identity

**替代方案：** 直接读取 JSON 密钥文件 → 不够通用，且 ADC 已覆盖此场景。

### D3: `api_key` 参数改为 `str | None = None`

**选择：** 将 `api_key` 类型从 `str` 改为 `str | None`，默认 `None`。

**理由：** ADC 模式下不需要 API Key，强制传入空字符串语义不清。

### D4: 新增 `google-auth` 依赖

**选择：** 在 `pyproject.toml` 中新增 `google-auth` 依赖。

**理由：** `google.auth.default()` 来自 `google-auth` 包，`google-genai` 不自动依赖它。

## Risks / Trade-offs

- **[ADC 环境未配置]** → 用户设置 `GEMINI_USE_ADC=true` 但未执行 `gcloud auth application-default login`，`google.auth.default()` 会抛异常。**缓解：** GeminiClient 构造时捕获异常并给出明确错误提示。
- **[google-auth 版本兼容]** → `google-auth` 与 `google-genai` 版本需兼容。**缓解：** 不锁定具体版本，由 uv 解析兼容版本。
