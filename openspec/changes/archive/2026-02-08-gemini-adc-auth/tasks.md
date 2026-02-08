## 1. 依赖与配置

- [x] 1.1 在 `pyproject.toml` 中添加 `google-auth` 依赖，运行 `uv sync`
- [x] 1.2 在 `app/config.py` 的 `Settings` 类中新增 `gemini_use_adc: bool = False`
- [x] 1.3 在 `.env.example` 的 AI 配置区新增 `GEMINI_USE_ADC=false` 及注释说明

## 2. GeminiClient ADC 支持

- [x] 2.1 修改 `app/ai/clients/gemini.py` 构造函数：`api_key` 改为 `str | None = None`，新增 `use_adc: bool = False`
- [x] 2.2 实现认证优先级逻辑：api_key 优先 → ADC → 抛出 ValueError
- [x] 2.3 ADC 模式下调用 `google.auth.default()` 获取 credentials，捕获异常并转为 ValueError

## 3. AIManager 适配

- [x] 3.1 修改 `app/ai/manager.py` 的 `_enabled` 判断为 `bool(api_key) or bool(use_adc)`
- [x] 3.2 修改 `_get_client()` 传入 `use_adc=self._settings.gemini_use_adc`
- [x] 3.3 更新禁用时的日志消息为 "AI 分析未启用：GEMINI_API_KEY 未配置且 ADC 未启用"

## 4. 文档更新

- [x] 4.1 更新 `README.md` 配置章节，补充 ADC 认证说明和使用方式
- [x] 4.2 更新 `CLAUDE.md`（如有需要）

## 5. 测试验证

- [x] 5.1 运行 `uv run pytest` 确认现有测试全部通过
