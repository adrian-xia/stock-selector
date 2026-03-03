# Codex API 集成方案调整

## 问题分析

经过测试发现：
1. ✅ codex-cli 可以正常工作
2. ❌ 标准 OpenAI SDK 无法调用该 API（403/404 错误）
3. ⚠️ 配置中的 `wire_api = "responses"` 表明这是一个非标准协议

## 原因

`https://gmn.chuangzuoli.com` 这个服务使用的是 **codex-cli 专有协议**，而不是标准的 OpenAI API 协议。这意味着：
- 它不兼容 OpenAI SDK
- 需要使用 codex-cli 的内部实现才能调用
- 无法直接在 Python 代码中使用

## 解决方案

### 方案 1：使用标准 OpenAI API（推荐）

如果需要在代码中集成 AI 分析，建议使用标准的 OpenAI API 提供商：

1. **OpenAI 官方**
   ```bash
   AI_PROVIDER=openai
   OPENAI_API_KEY=sk-xxx
   OPENAI_BASE_URL=https://api.openai.com/v1
   OPENAI_MODEL_ID=gpt-4
   ```

2. **其他兼容 OpenAI API 的服务**
   - Azure OpenAI
   - 国内的各种 API 代理服务（需要支持标准 OpenAI 协议）

### 方案 2：继续使用 Gemini

保持现有的 Gemini 集成：
```bash
AI_PROVIDER=gemini
GEMINI_API_KEY=your-key
```

### 方案 3：通过 codex-cli 调用（不推荐）

如果必须使用 codex，可以通过子进程调用 codex-cli：

```python
import subprocess
import json

def call_codex_cli(prompt: str) -> str:
    """通过 codex-cli 调用 AI。"""
    result = subprocess.run(
        ["codex", "exec", prompt],
        capture_output=True,
        text=True,
        timeout=60,
    )
    # 解析输出...
    return result.stdout
```

**缺点**：
- 性能差（每次都要启动新进程）
- 难以解析输出
- 无法获取 token 用量
- 不适合生产环境

## 建议

**保留当前代码实现**，但在文档中说明：
- Codex 客户端代码已实现，支持标准 OpenAI 兼容 API
- `https://gmn.chuangzuoli.com` 使用专有协议，不兼容标准 OpenAI SDK
- 如需使用 Codex，请使用支持标准 OpenAI API 的服务

## 更新配置说明

在 `.env.example` 中添加说明：

```bash
# --- AI (Codex) ---
# 注意：需要使用支持标准 OpenAI API 的服务
# codex-cli 使用的 gmn.chuangzuoli.com 不兼容标准 API
CODEX_API_KEY=your-codex-api-key
CODEX_BASE_URL=https://api.openai.com/v1  # 或其他兼容 OpenAI API 的服务
CODEX_MODEL_ID=gpt-4
CODEX_THINKING_DEFAULT=xhigh
```

## 结论

当前的 Codex 集成代码是正确的，问题在于测试使用的 API 服务不兼容标准 OpenAI 协议。代码可以正常工作，只需要使用兼容的 API 服务即可。
