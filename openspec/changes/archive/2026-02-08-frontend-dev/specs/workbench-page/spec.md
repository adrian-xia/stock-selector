## ADDED Requirements

### Requirement: 策略列表加载与展示
系统 SHALL 在工作台页面左侧面板展示所有可用策略，按分类（技术面/基本面）分组显示，每个策略显示名称和简要描述。

#### Scenario: 页面加载时获取策略列表
- **WHEN** 用户进入选股工作台页面
- **THEN** 系统调用 `GET /api/v1/strategy/list` 获取策略列表并按分类分组展示

#### Scenario: 策略列表加载失败
- **WHEN** 策略列表 API 请求失败
- **THEN** 显示错误提示，提供重试按钮

### Requirement: 策略选择与参数配置
系统 SHALL 允许用户从策略列表中选择多个策略，并为每个选中的策略配置参数（使用策略的 default_params 作为初始值）。

#### Scenario: 选择策略
- **WHEN** 用户点击策略列表中的某个策略
- **THEN** 该策略被添加到已选策略区域，显示其默认参数

#### Scenario: 修改策略参数
- **WHEN** 用户修改已选策略的参数值
- **THEN** 参数值实时更新，用于后续选股执行

#### Scenario: 移除已选策略
- **WHEN** 用户点击已选策略的删除按钮
- **THEN** 该策略从已选列表中移除

### Requirement: 基础过滤配置
系统 SHALL 提供基础过滤选项：剔除 ST 股票（默认开启）、剔除停牌股票（默认开启）。

#### Scenario: 默认过滤配置
- **WHEN** 用户进入工作台页面
- **THEN** 「剔除 ST」和「剔除停牌」复选框默认勾选

### Requirement: 执行选股
系统 SHALL 提供「运行筛选」按钮，点击后调用 `POST /api/v1/strategy/run` 执行选股，执行期间按钮显示 loading 状态。

#### Scenario: 正常执行选股
- **WHEN** 用户选择了至少一个策略并点击「运行筛选」
- **THEN** 系统发送请求到后端，按钮显示 loading，完成后展示结果

#### Scenario: 未选择策略时执行
- **WHEN** 用户未选择任何策略就点击「运行筛选」
- **THEN** 提示用户至少选择一个策略

#### Scenario: 选股执行失败
- **WHEN** 后端返回错误
- **THEN** 显示错误提示信息，按钮恢复可点击状态

### Requirement: 选股结果表格
系统 SHALL 在右侧面板以 Ant Design Table 展示选股结果，列包括：代码、名称、现价、涨跌幅、匹配策略数、AI 评分、AI 信号。表格支持按列排序。

#### Scenario: 结果展示
- **WHEN** 选股执行完成
- **THEN** 右侧表格展示结果列表，显示 layer_stats 统计信息和耗时

#### Scenario: 按 AI 评分排序
- **WHEN** 用户点击「AI 评分」列头
- **THEN** 表格按 AI 评分降序/升序排列

#### Scenario: 无结果
- **WHEN** 选股执行完成但无匹配股票
- **THEN** 表格显示空状态提示

### Requirement: 股票详情展示
系统 SHALL 在用户点击结果表格中的某只股票时，在底部面板展示该股票的详细信息：匹配的策略列表和 AI 分析摘要。

#### Scenario: 查看股票详情
- **WHEN** 用户点击结果表格中的一行
- **THEN** 底部面板展示该股票的匹配策略列表和 AI 分析摘要（如有）

#### Scenario: AI 分析未启用
- **WHEN** 选股结果中 ai_enabled 为 false
- **THEN** 详情面板不显示 AI 相关信息
