# Codex API 集成说明

## 已完成的工作

### 1. 代码实现

- ✅ 创建 `app/ai/clients/codex.py` - Codex API 客户端
- ✅ 修改 `app/config.py` - 添加 AI 提供商配置和 Codex 相关配置
- ✅ 修改 `app/ai/manager.py` - 支持多 AI 提供商（Gemini/Codex）
- ✅ 更新 `pyproject.toml` - 添加 openai 依赖
- ✅ 更新 `.env.example` - 添加 Codex 配置示例
- ✅ 更新 `docker/.env.docker` - 添加 Codex 配置

### 2. 配置项

在 `.env` 文件中添加以下配置：

```bash
# --- AI Provider (AI 提供商选择) ---
AI_PROVIDER=codex                            # 可选：gemini/codex（为空则禁用 AI）

# --- AI (Codex) ---
# 注意：需要使用支持标准 OpenAI API 的服务
CODEX_API_KEY=your-api-key-here
CODEX_BASE_URL=https://api.openai.com/v1    # 或其他兼容 OpenAI API 的服务
CODEX_MODEL_ID=gpt-4
CODEX_THINKING_DEFAULT=xhigh                 # 思考模式：xhigh/high/medium/low
CODEX_MAX_TOKENS=4000
CODEX_TIMEOUT=30
CODEX_MAX_RETRIES=2
```

### 3. 使用方式

切换 AI 提供商只需修改 `AI_PROVIDER` 配置：

```bash
# 使用 Gemini
AI_PROVIDER=gemini

# 使用 Codex（或其他 OpenAI 兼容服务）
AI_PROVIDER=codex

# 禁用 AI
AI_PROVIDER=
```

## 重要说明

### 关于 API 兼容性

**CodexClient 实现基于标准 OpenAI API 协议**，可以与以下服务配合使用：

✅ **兼容的服务**：
- OpenAI 官方 API（`https://api.openai.com/v1`）
- Azure OpenAI Service
- 其他支持标准 OpenAI API 协议的服务

❌ **不兼容的服务**：
- codex-cli 专用的 `https://gmn.chuangzuoli.com`（使用专有协议 `wire_api = "responses"`）

### codex-cli vs CodexClient

- **codex-cli**：命令行工具，使用专有协议与特定服务通信
- **CodexClient**：Python 客户端，使用标准 OpenAI API 协议

两者虽然名字相似，但使用不同的通信协议，不能互换。

## 代码特性

### CodexClient 特性

- 支持自定义 base_url
- 支持 thinking 参数（xhigh/high/medium/low）
- 支持 JSON 模式（response_format="json_object"）
- 自动重试机制（指数退避）
- Token 用量统计
- 超时控制

### AIManager 特性

- 多提供商支持（Gemini/Codex）
- 延迟初始化客户端
- 每日调用上限控制
- 结果持久化
- 失败降级（AI 失败不影响主流程）

## 测试命令

```bash
# 安装依赖
uv sync --extra dev

# 测试 Codex 客户端（需要有效的 OpenAI API Key）
export CODEX_API_KEY="your-openai-api-key"
export PYTHONPATH=/Users/adrian/Developer/Codes/stock-selector
uv run python tests/test_codex_client.py

# 或使用 pytest
uv run pytest tests/test_codex_client.py -v
```

## 生产部署

```bash
# 更新 .env 或 docker/.env.docker
AI_PROVIDER=codex
CODEX_API_KEY=your-production-key
CODEX_BASE_URL=https://api.openai.com/v1
CODEX_MODEL_ID=gpt-4

# Docker 部署
docker compose down
docker compose up -d --build
docker compose logs -f
```
