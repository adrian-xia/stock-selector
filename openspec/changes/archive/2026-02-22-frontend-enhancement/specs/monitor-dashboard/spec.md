## ADDED Requirements

### Requirement: 监控页面组件拆分
MonitorPage SHALL 拆分为独立子组件：WatchlistTable（自选股行情表格）、AlertRulePanel（告警规则管理）、AlertHistoryPanel（告警历史）。

#### Scenario: 子组件独立渲染
- **WHEN** 用户访问 /monitor 页面
- **THEN** 三个子组件 SHALL 独立渲染，各自管理自己的数据获取和状态

### Requirement: 监控页面 React Query 迁移
MonitorPage 及其子组件 SHALL 使用 React Query 管理所有 API 数据获取，替代当前的手动 useState/useEffect 模式。

#### Scenario: 告警规则列表使用 React Query
- **WHEN** AlertRulePanel 组件挂载
- **THEN** SHALL 通过 React Query useQuery 获取告警规则列表
- **AND** 加载中 SHALL 显示 Table loading 状态
- **AND** 失败 SHALL 显示 QueryErrorAlert 组件

#### Scenario: 告警历史使用 React Query 轮询
- **WHEN** AlertHistoryPanel 组件挂载
- **THEN** SHALL 通过 React Query useQuery 获取告警历史
- **AND** SHALL 配置 refetchInterval: 30000 实现自动轮询

#### Scenario: 自选股列表使用 React Query
- **WHEN** WatchlistTable 组件挂载
- **THEN** SHALL 通过 React Query useQuery 获取自选股列表
- **AND** 添加/移除自选股 SHALL 通过 useMutation + invalidateQueries 实现

### Requirement: 监控页面错误状态可见化
MonitorPage SHALL 将所有 API 错误通过 UI 展示给用户，不再静默失败。

#### Scenario: API 请求失败时显示错误
- **WHEN** 任何监控相关 API 请求失败
- **THEN** SHALL 在对应区域显示 QueryErrorAlert 组件
- **AND** SHALL 不再使用空 catch 块静默忽略错误
