# Codex API 集成说明

## 已完成的工作

### 1. 代码实现

- ✅ 创建 `app/ai/clients/codex.py` - Codex API 客户端（gmn.chuangzuoli.com 专有协议）
- ✅ 修改 `app/config.py` - 添加 AI 提供商配置和 Codex 相关配置
- ✅ 修改 `app/ai/manager.py` - 统一通过 Codex 网关处理 AI 请求
- ✅ 更新 `pyproject.toml` - 添加 httpx 依赖
- ✅ 更新 `.env.example` - 添加 Codex 配置示例
- ✅ 更新 `docker/.env.docker` - 添加 Codex 配置

### 2. 配置项

在 `.env` 文件中添加以下配置：

```bash
# --- AI Provider (AI 提供商选择) ---
AI_PROVIDER=codex                            # 固定：codex（为空则禁用 AI）

# --- AI (Codex) ---
CODEX_API_KEY=your-api-key-here
CODEX_BASE_URL=https://gmn.chuangzuoli.com  # gmn.chuangzuoli.com 专有协议
CODEX_MODEL_ID=gpt-5.3-codex
CODEX_THINKING_DEFAULT=xhigh                 # 思考模式：xhigh/high/medium/low
CODEX_MAX_TOKENS=4000
CODEX_TIMEOUT=30
CODEX_MAX_RETRIES=2
```

### 3. 使用方式

当前 AI 实现固定使用 Codex：

```bash
AI_PROVIDER=codex

# 禁用 AI
AI_PROVIDER=
```

## API 协议说明

### gmn.chuangzuoli.com 专有协议

**请求格式**：

```json
{
  "model": "gpt-5.3-codex",
  "input": [
    {
      "type": "message",
      "role": "user",
      "content": [
        {
          "type": "input_text",
          "text": "你的问题"
        }
      ]
    }
  ]
}
```

**响应格式**：

```json
{
  "id": "resp_xxx",
  "status": "completed",
  "output": [
    {
      "type": "message",
      "content": [
        {
          "type": "output_text",
          "text": "模型的回答"
        }
      ]
    }
  ],
  "usage": {
    "input_tokens": 1571,
    "output_tokens": 45,
    "total_tokens": 1616
  }
}
```

**关键特性**：
- 使用 `/v1/responses` 端点（不是标准的 `/v1/chat/completions`）
- 请求体使用 `input` 数组（不是 `messages`）
- 消息格式是嵌套的 `content` 数组结构
- 响应使用 `output` 数组，包含 `output_text` 类型

## 代码特性

### CodexClient 特性

- 使用 httpx 直接发送 HTTP 请求
- 支持 gmn.chuangzuoli.com 专有协议
- 支持 JSON 模式（`text.format.type: "json_object"`）
- 自动重试机制（指数退避）
- Token 用量统计
- 超时控制

### AIManager 特性

- 统一 Codex 网关
- 延迟初始化客户端
- 每日调用上限控制
- 结果持久化
- 失败降级（AI 失败不影响主流程）

## 测试命令

```bash
# 安装依赖
uv sync --extra dev

# 测试 Codex 客户端
export CODEX_API_KEY="your-api-key"
export PYTHONPATH=/Users/adrian/Developer/Codes/stock-selector
uv run python tests/test_codex_gmn.py

# 或使用 pytest
uv run pytest tests/test_codex_gmn.py -v
```

## 生产部署

```bash
# 更新 .env 或 docker/.env.docker
AI_PROVIDER=codex
CODEX_API_KEY=your-production-key
CODEX_BASE_URL=https://gmn.chuangzuoli.com
CODEX_MODEL_ID=gpt-5.3-codex

# Docker 部署
docker compose down
docker compose up -d --build
docker compose logs -f
```
