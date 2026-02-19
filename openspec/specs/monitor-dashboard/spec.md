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
