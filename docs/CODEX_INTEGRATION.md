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
CODEX_API_KEY=your-codex-api-key-here
CODEX_BASE_URL=https://gmn.chuangzuoli.com/v1
CODEX_MODEL_ID=gpt-5.3-codex
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

# 使用 Codex
AI_PROVIDER=codex

# 禁用 AI
AI_PROVIDER=
```

### 4. API 测试问题

**当前状态**：测试 API Key 时遇到 403 Forbidden 错误。

**可能原因**：
1. API Key 无效或权限不足
2. IP 地址未加入白名单
3. Cloudflare 防火墙规则阻止请求
4. 服务端配置问题

**测试结果**：
- ✅ 代码实现完成
- ✅ 配置项添加完成
- ✅ 依赖安装完成
- ❌ API 连接测试失败（403 Forbidden）

**建议**：
1. 检查 API Key 是否有效
2. 联系 API 提供商确认 IP 白名单
3. 确认 base_url 是否正确
4. 检查是否需要特殊的认证方式

### 5. 代码特性

**CodexClient 特性**：
- 支持自定义 base_url
- 支持 thinking 参数（xhigh/high/medium/low）
- 支持 JSON 模式（response_format="json_object"）
- 自动重试机制（指数退避）
- Token 用量统计
- 超时控制

**AIManager 特性**：
- 多提供商支持（Gemini/Codex）
- 延迟初始化客户端
- 每日调用上限控制
- 结果持久化
- 失败降级（AI 失败不影响主流程）

## 下一步

1. **验证 API Key**：联系 API 提供商确认 Key 是否有效
2. **IP 白名单**：如果需要，将服务器 IP 加入白名单
3. **完整测试**：API Key 问题解决后，运行完整的集成测试
4. **文档更新**：将 Codex 配置说明添加到 README.md

## 测试命令

```bash
# 安装依赖
uv sync --extra dev

# 测试 Codex 客户端
export CODEX_API_KEY="your-key-here"
export PYTHONPATH=/Users/adrian/Developer/Codes/stock-selector
uv run python tests/test_codex_client.py

# 或使用 pytest
uv run pytest tests/test_codex_client.py -v
```
