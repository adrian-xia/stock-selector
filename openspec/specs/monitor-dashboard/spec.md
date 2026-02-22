## ADDED Requirements

### Requirement: Monitor dashboard page
The system SHALL provide a realtime monitoring dashboard page accessible from the main navigation.

#### Scenario: Navigate to monitor page
- **WHEN** user clicks "实时监控" in the sidebar navigation
- **THEN** the system SHALL display the monitoring dashboard with watchlist quotes, signal indicators, and alert history sections

---

### Requirement: Watchlist realtime quotes display
The dashboard SHALL display realtime quotes for the user's watchlist stocks.

#### Scenario: Display realtime prices
- **WHEN** the dashboard is open and WebSocket is connected
- **THEN** it SHALL display each watchlist stock with current price, change amount, change percent, volume, and last update time, updating in realtime

#### Scenario: Visual price change indication
- **WHEN** a stock's price changes
- **THEN** the cell SHALL briefly flash green (price up) or red (price down) to indicate the change

#### Scenario: WebSocket disconnected
- **WHEN** the WebSocket connection is lost
- **THEN** the dashboard SHALL display a "连接断开" banner and attempt to reconnect every 5 seconds

---

### Requirement: Watchlist management
The dashboard SHALL allow users to manage their monitored stock list.

#### Scenario: Add stock to watchlist
- **WHEN** user searches and selects a stock to add
- **THEN** the system SHALL add it to the watchlist and start receiving realtime quotes via WebSocket

#### Scenario: Remove stock from watchlist
- **WHEN** user removes a stock from the watchlist
- **THEN** the system SHALL unsubscribe from its WebSocket channel and remove it from display

#### Scenario: Watchlist limit
- **WHEN** user attempts to add a stock beyond the 50-stock limit
- **THEN** the system SHALL show an error message indicating the limit

---

### Requirement: Signal indicator display
The dashboard SHALL display strategy signal indicators alongside realtime quotes.

#### Scenario: Show active signals
- **WHEN** a strategy signal is detected for a watchlist stock
- **THEN** the dashboard SHALL display a signal badge (e.g., "MA金叉", "RSI超卖") next to the stock

#### Scenario: Signal expiry
- **WHEN** a signal was triggered more than 60 minutes ago with no new trigger
- **THEN** the signal badge SHALL be dimmed or removed

---

### Requirement: Alert history panel
The dashboard SHALL display recent alert history.

#### Scenario: Show recent alerts
- **WHEN** the dashboard is loaded
- **THEN** it SHALL display the 20 most recent alerts with timestamp, stock code, alert type, and message

#### Scenario: Realtime alert notification
- **WHEN** a new alert is triggered while the dashboard is open
- **THEN** the dashboard SHALL display an Ant Design notification popup and prepend the alert to the history list

---

### Requirement: Alert rule management
The dashboard SHALL provide UI for managing alert rules.

#### Scenario: Create alert rule from dashboard
- **WHEN** user clicks "添加预警" on a watchlist stock
- **THEN** a modal SHALL appear allowing configuration of rule type, parameters, and cooldown

#### Scenario: View and toggle rules
- **WHEN** user opens the alert rules panel
- **THEN** it SHALL display all rules with toggle switches to enable/disable each rule

---

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
