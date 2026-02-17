## ADDED Requirements

### Requirement: YAML Prompt 模板管理
系统 SHALL 从 YAML 文件加载 Prompt 模板，替代硬编码方式。模板文件位于 `app/ai/prompts/` 目录。

#### Scenario: 加载默认模板
- **WHEN** 调用 `build_analysis_prompt()` 构建 Prompt
- **THEN** SHALL 从 `app/ai/prompts/stock_analysis_v1.yaml` 加载模板

#### Scenario: 模板包含版本号
- **WHEN** 加载 YAML 模板
- **THEN** 模板 SHALL 包含 version 字段，用于记录到 ai_analysis_results.prompt_version

#### Scenario: 模板格式
- **WHEN** 读取 YAML 模板文件
- **THEN** SHALL 包含 version、system_prompt、user_prompt_template、output_schema 字段
