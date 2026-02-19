## ADDED Requirements

### Requirement: Realtime quote data collection
The system SHALL collect realtime quote data for monitored stocks from Tushare Pro during trading hours (9:15-15:00 on trading days).

#### Scenario: Collect quotes during trading hours
- **WHEN** the system is running during A-share trading hours on a trading day
- **THEN** it SHALL poll Tushare Pro every 3 seconds for all monitored stocks (up to 50)

#### Scenario: Stop collection outside trading hours
- **WHEN** the current time is outside trading hours or on a non-trading day
- **THEN** the system SHALL NOT poll for realtime quotes

#### Scenario: Handle API failure
- **WHEN** Tushare API call fails 3 consecutive times
- **THEN** the system SHALL pause collection for 1 minute, log a WARNING, and retry

---

### Requirement: Redis Pub/Sub quote distribution
The system SHALL distribute realtime quotes via Redis Pub/Sub channels.

#### Scenario: Publish quote update
- **WHEN** new quote data is received from Tushare
- **THEN** it SHALL publish to Redis channel `market:realtime:{ts_code}` with latest price, volume, change percent, and timestamp

#### Scenario: Redis unavailable
- **WHEN** Redis is not available
- **THEN** the system SHALL log a WARNING and continue collecting (quotes will be lost but system remains stable)

---

### Requirement: WebSocket realtime push
The system SHALL provide a WebSocket endpoint for clients to subscribe to realtime quote updates.

#### Scenario: Client subscribes to stocks
- **WHEN** a client sends a subscribe message with a list of ts_codes via WebSocket
- **THEN** the server SHALL start pushing realtime quotes for those stocks to the client

#### Scenario: Client unsubscribes
- **WHEN** a client sends an unsubscribe message for specific ts_codes
- **THEN** the server SHALL stop pushing quotes for those stocks to the client

#### Scenario: Heartbeat keepalive
- **WHEN** no data is sent for 30 seconds
- **THEN** the server SHALL send a ping frame to keep the connection alive

#### Scenario: Client disconnects
- **WHEN** a WebSocket connection is closed
- **THEN** the server SHALL clean up all subscriptions for that client

#### Scenario: Subscription limit
- **WHEN** a client attempts to subscribe to more than 50 stocks total
- **THEN** the server SHALL reject the subscription with an error message

---

### Requirement: Realtime indicator calculation
The system SHALL calculate key technical indicators for monitored stocks every 60 seconds during trading hours.

#### Scenario: Calculate indicators
- **WHEN** 60 seconds have elapsed since last calculation during trading hours
- **THEN** the system SHALL compute MA(5,10,20), MACD, and RSI for all monitored stocks using latest realtime price combined with historical daily data

#### Scenario: Detect strategy signal
- **WHEN** indicator calculation detects a signal trigger (e.g., MA golden cross, RSI oversold)
- **THEN** the system SHALL emit an alert event to the alert engine
