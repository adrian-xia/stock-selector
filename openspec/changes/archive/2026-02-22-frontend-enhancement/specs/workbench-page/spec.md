## MODIFIED Requirements

### Requirement: 股票详情展示
系统 SHALL 在用户点击结果表格中的某只股票时，在底部面板展示该股票的详细信息：匹配的策略列表、AI 分析摘要和 K 线走势图。

#### Scenario: 查看股票详情
- **WHEN** 用户点击结果表格中的一行
- **THEN** 底部面板展示该股票的匹配策略列表、AI 分析摘要（如有）和 K 线走势图

#### Scenario: AI 分析未启用
- **WHEN** 选股结果中 ai_enabled 为 false
- **THEN** 详情面板不显示 AI 相关信息

#### Scenario: K 线图加载
- **WHEN** 用户点击某只股票展开详情
- **THEN** SHALL 通过 `fetchKline` API 加载该股票最近 120 个交易日的 K 线数据
- **AND** 加载期间 SHALL 显示 Spin 加载状态

## ADDED Requirements

### Requirement: 工作台错误处理统一化
工作台页面 SHALL 使用 QueryErrorAlert 组件统一展示 API 错误。

#### Scenario: 策略列表加载失败
- **WHEN** 策略列表 API 请求失败
- **THEN** SHALL 显示 QueryErrorAlert 组件，包含错误信息和重试按钮
