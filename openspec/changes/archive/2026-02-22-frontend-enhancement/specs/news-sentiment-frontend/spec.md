## ADDED Requirements

### Requirement: 新闻页面 React Query 迁移
NewsPage SHALL 使用 React Query 管理所有 API 数据获取，替代当前的手动 useState/useEffect 模式。

#### Scenario: 新闻列表使用 React Query
- **WHEN** 用户访问 /news 页面
- **THEN** 新闻列表 SHALL 通过 React Query useQuery 获取
- **AND** 加载中 SHALL 显示 Table loading 状态
- **AND** 失败 SHALL 显示 QueryErrorAlert 组件

#### Scenario: 情感趋势使用 React Query
- **WHEN** 用户选择股票代码查看情感趋势
- **THEN** 情感趋势数据 SHALL 通过 React Query useQuery 获取
- **AND** 查询 key SHALL 包含股票代码，切换股票时自动重新请求

#### Scenario: 每日情感摘要使用 React Query
- **WHEN** 用户选择日期查看情感摘要
- **THEN** 摘要数据 SHALL 通过 React Query useQuery 获取
- **AND** 查询 key SHALL 包含日期，切换日期时自动重新请求

### Requirement: 新闻页面加载和错误 UI 统一化
NewsPage SHALL 使用统一的加载和错误 UI 组件。

#### Scenario: 情感趋势图加载状态
- **WHEN** 情感趋势数据正在加载
- **THEN** 图表区域 SHALL 显示 Spin 加载状态

#### Scenario: 情感趋势图加载失败
- **WHEN** 情感趋势 API 请求失败
- **THEN** 图表区域 SHALL 显示 QueryErrorAlert 组件
