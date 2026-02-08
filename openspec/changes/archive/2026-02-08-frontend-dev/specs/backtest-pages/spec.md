## ADDED Requirements

### Requirement: 回测任务列表页
系统 SHALL 在 `/backtest` 路由展示回测任务列表，以 Ant Design Table 分页展示，列包括：任务 ID、策略名称、股票数量、时间范围、状态、年化收益率、创建时间。支持按创建时间倒序排列。

#### Scenario: 加载回测列表
- **WHEN** 用户进入回测中心页面
- **THEN** 系统调用 `GET /api/v1/backtest/list` 获取任务列表并展示

#### Scenario: 列表为空
- **WHEN** 没有任何回测任务
- **THEN** 显示空状态提示和「新建回测」按钮

#### Scenario: 点击查看详情
- **WHEN** 用户点击列表中的某个任务行
- **THEN** 导航到 `/backtest/:taskId` 详情页

### Requirement: 新建回测向导
系统 SHALL 在 `/backtest/new` 路由提供回测配置表单，包含：策略选择（下拉框）、股票代码输入（支持多个，逗号分隔）、时间范围选择（日期范围选择器）、初始资金输入（默认 100 万）。

#### Scenario: 填写回测配置
- **WHEN** 用户进入新建回测页面
- **THEN** 显示配置表单，初始资金默认为 1000000

#### Scenario: 提交回测
- **WHEN** 用户填写完配置并点击「开始回测」
- **THEN** 系统调用 `POST /api/v1/backtest/run`，提交后导航到结果详情页

#### Scenario: 表单校验
- **WHEN** 用户未填写必填项（策略、股票代码、时间范围）
- **THEN** 显示对应字段的校验错误提示

#### Scenario: 日期范围校验
- **WHEN** 用户选择的开始日期晚于或等于结束日期
- **THEN** 显示日期范围错误提示

### Requirement: 回测结果详情页
系统 SHALL 在 `/backtest/:taskId` 路由展示回测结果，包含三个区域：绩效指标卡片、收益曲线图、交易明细表。

#### Scenario: 加载完成的回测结果
- **WHEN** 用户访问已完成的回测任务详情页
- **THEN** 展示绩效指标（年化收益率、最大回撤、夏普比率、胜率等）、收益曲线图和交易明细表

#### Scenario: 回测任务不存在
- **WHEN** 用户访问不存在的 taskId
- **THEN** 显示 404 提示

### Requirement: 绩效指标卡片
系统 SHALL 以 Ant Design Statistic 卡片组展示核心绩效指标：年化收益率、最大回撤、夏普比率、胜率、总交易次数、盈亏比。收益率为正显示绿色，为负显示红色。

#### Scenario: 指标展示
- **WHEN** 回测结果加载完成
- **THEN** 以卡片形式展示 6 个核心指标，百分比类指标格式化为百分数

### Requirement: 收益曲线图
系统 SHALL 使用 ECharts 折线图展示回测净值曲线（equity_curve），X 轴为日期，Y 轴为净值。

#### Scenario: 曲线渲染
- **WHEN** 回测结果包含 equity_curve 数据
- **THEN** 渲染折线图，支持鼠标悬停查看具体日期和净值

#### Scenario: 无曲线数据
- **WHEN** equity_curve 为空
- **THEN** 显示「暂无净值数据」提示

### Requirement: 交易明细表
系统 SHALL 以 Ant Design Table 展示交易明细，列包括：股票代码、方向（买入/卖出）、日期、价格、数量、手续费、盈亏。买入方向显示红色，卖出显示绿色。

#### Scenario: 交易明细展示
- **WHEN** 回测结果包含 trades 数据
- **THEN** 以表格展示所有交易记录，支持分页

### Requirement: 回测状态轮询
系统 SHALL 对状态为 pending 或 running 的回测任务进行轮询（每 3 秒），任务完成或失败后自动停止轮询并刷新页面数据。

#### Scenario: 轮询进行中的任务
- **WHEN** 用户访问状态为 running 的回测详情页
- **THEN** 页面显示 loading 状态，每 3 秒轮询一次 `GET /api/v1/backtest/result/:taskId`

#### Scenario: 轮询到完成状态
- **WHEN** 轮询返回 status 为 completed
- **THEN** 停止轮询，展示完整的回测结果

#### Scenario: 回测失败
- **WHEN** 轮询返回 status 为 failed
- **THEN** 停止轮询，显示错误信息
