## Why

当前 GeminiClient 仅支持 API Key 认证。用户持有 Google AI Pro 账号，需要通过 Application Default Credentials (ADC) 方式调用 Gemini API，避免手动管理 API Key。

## What Changes

- GeminiClient 构造函数新增 `use_adc` 参数，支持 ADC 认证方式初始化 `genai.Client`
- `api_key` 参数改为可选（`str | None = None`），与 `use_adc` 二选一
- `app/config.py` 新增 `GEMINI_USE_ADC` 配置项
- AIManager 启用判断从"有 API Key"改为"有 API Key 或启用 ADC"
- `.env.example` 和 `README.md` 补充 ADC 配置说明
- 新增 `google-auth` 依赖

## Capabilities

### New Capabilities

（无新增能力模块）

### Modified Capabilities

- `gemini-client`: 构造函数新增 ADC 认证方式，`api_key` 改为可选
- `app-config`: 新增 `GEMINI_USE_ADC` 配置项
- `ai-manager`: 启用判断逻辑扩展为支持 ADC 模式

## Impact

- **代码文件：** `app/ai/clients/gemini.py`、`app/config.py`、`app/ai/manager.py`
- **配置文件：** `.env.example`、`README.md`
- **依赖：** 新增 `google-auth` 包
- **API：** 无变化
- **数据库：** 无变化
