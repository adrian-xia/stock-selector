# Codex API 快速开始

## 配置

在 `.env` 文件中添加：

```bash
AI_PROVIDER=codex
CODEX_API_KEY=your-api-key-here
CODEX_BASE_URL=https://gmn.chuangzuoli.com
CODEX_MODEL_ID=gpt-5.3-codex
```

## 使用示例

### 1. 直接使用 CodexClient

```python
from app.ai.clients.codex import CodexClient

async def example():
    client = CodexClient(
        api_key="your-api-key",
        base_url="https://gmn.chuangzuoli.com",
        model_id="gpt-5.3-codex",
    )

    try:
        # 文本响应
        response = await client.chat("你好，请介绍一下 A 股市场")
        print(response)

        # JSON 响应
        json_response = await client.chat_json(
            '请返回 JSON: {"market": "A股", "feature": "特点"}'
        )
        print(json_response)

        # Token 用量
        usage = client.get_last_usage()
        print(f"Token 用量: {usage}")

    finally:
        await client.close()
```

### 2. 通过 AIManager 使用

```python
from app.ai.manager import AIManager
from app.config import Settings

async def example():
    settings = Settings(
        ai_provider="codex",
        codex_api_key="your-api-key",
    )

    manager = AIManager(settings)

    if manager.is_enabled:
        # AIManager 会自动选择正确的客户端
        client = manager._get_client()
        response = await client.chat("分析一下当前市场")
        print(response)
```

### 3. 切换 AI 提供商

```python
# 使用 Codex
settings = Settings(ai_provider="codex", codex_api_key="...")

# 禁用 AI
settings = Settings(ai_provider="")
```

## 测试

```bash
# 设置环境变量
export CODEX_API_KEY="your-api-key"
export PYTHONPATH=/path/to/project

# 运行测试
uv run python tests/test_codex_gmn.py
uv run python tests/test_ai_manager_codex.py
```

## 常见问题

### Q: 如何查看 API 调用详情？

A: 设置日志级别为 DEBUG：

```bash
LOG_LEVEL=DEBUG uv run uvicorn app.main:app
```

### Q: 如何限制每日 AI 调用次数？

A: 在 `.env` 中设置：

```bash
AI_DAILY_CALL_LIMIT=100  # 每日最多 100 次
```

### Q: API 调用失败怎么办？

A: CodexClient 会自动重试 2 次（指数退避），如果仍然失败会抛出 `CodexAPIError`。

### Q: 如何处理超时？

A: 调整超时时间：

```bash
CODEX_TIMEOUT=60  # 60 秒超时
```

## 更多信息

- [完整集成文档](./CODEX_INTEGRATION.md)
- [完成总结](./CODEX_COMPLETION_SUMMARY.md)
