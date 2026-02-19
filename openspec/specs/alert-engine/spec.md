## ADDED Requirements

### Requirement: Alert rule configuration
The system SHALL allow users to create, update, delete, and list alert rules via REST API.

#### Scenario: Create price alert rule
- **WHEN** user creates a rule with type "price_break", ts_code, target_price, and direction (above/below)
- **THEN** the system SHALL persist the rule to alert_rules table and return the created rule with ID

#### Scenario: Create strategy signal rule
- **WHEN** user creates a rule with type "strategy_signal", ts_code, and signal_type (e.g., ma_golden_cross, rsi_oversold)
- **THEN** the system SHALL persist the rule and return the created rule with ID

#### Scenario: List active rules
- **WHEN** user requests all alert rules
- **THEN** the system SHALL return all rules with their enabled status and last triggered time

#### Scenario: Toggle rule enabled status
- **WHEN** user updates a rule's enabled field
- **THEN** the system SHALL update the rule and only evaluate enabled rules during monitoring

#### Scenario: Delete rule
- **WHEN** user deletes a rule by ID
- **THEN** the system SHALL remove the rule from alert_rules table

---

### Requirement: Alert signal detection
The system SHALL evaluate active alert rules against realtime data and trigger alerts when conditions are met.

#### Scenario: Price break above threshold
- **WHEN** a stock's realtime price crosses above the target_price of an active "price_break" rule with direction "above"
- **THEN** the system SHALL trigger an alert event with rule details and current price

#### Scenario: Price break below threshold
- **WHEN** a stock's realtime price crosses below the target_price of an active "price_break" rule with direction "below"
- **THEN** the system SHALL trigger an alert event

#### Scenario: Strategy signal triggered
- **WHEN** the realtime indicator calculation emits a signal matching an active "strategy_signal" rule
- **THEN** the system SHALL trigger an alert event

---

### Requirement: Alert cooldown (anti-flapping)
The system SHALL enforce a cooldown period after each alert trigger to prevent repeated notifications.

#### Scenario: Cooldown active
- **WHEN** an alert rule was triggered within its cooldown_minutes period
- **THEN** the system SHALL NOT trigger the same rule again until cooldown expires

#### Scenario: Cooldown expired
- **WHEN** the cooldown period for a rule has expired
- **THEN** the system SHALL allow the rule to trigger again if conditions are met

#### Scenario: Default cooldown
- **WHEN** a rule does not specify cooldown_minutes
- **THEN** the system SHALL use a default cooldown of 30 minutes

---

### Requirement: Alert history persistence
The system SHALL persist all triggered alerts to the alert_history table.

#### Scenario: Record triggered alert
- **WHEN** an alert is triggered
- **THEN** the system SHALL insert a record with rule_id, ts_code, triggered_at, message, and notified status

#### Scenario: Query alert history
- **WHEN** user requests alert history via API with optional filters (ts_code, date range)
- **THEN** the system SHALL return paginated alert history sorted by triggered_at descending

---

### Requirement: Multi-channel notification dispatch
The system SHALL send notifications through configured channels when an alert is triggered.

#### Scenario: Send WeChat Work notification
- **WHEN** an alert is triggered and WeChat Work webhook URL is configured
- **THEN** the system SHALL POST a markdown message to the webhook with stock code, alert type, and current price

#### Scenario: Send Telegram notification
- **WHEN** an alert is triggered and Telegram bot token and chat_id are configured
- **THEN** the system SHALL send a message via Telegram Bot API with alert details

#### Scenario: Channel not configured
- **WHEN** a notification channel is not configured (no webhook URL or token)
- **THEN** the system SHALL skip that channel and log the alert to application log only

#### Scenario: Notification failure
- **WHEN** a notification channel fails to deliver
- **THEN** the system SHALL log a WARNING, mark notified=false in alert_history, and NOT retry (fire-and-forget)
