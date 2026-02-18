## ADDED Requirements

### Requirement: announcements table
The system SHALL provide an `announcements` database table with the following columns:

- `id` (int, PK, autoincrement)
- `ts_code` (str, not null, indexed)
- `title` (str, not null)
- `summary` (text, nullable)
- `source` (str, not null) — "eastmoney", "taoguba", "xueqiu"
- `pub_date` (date, not null, indexed)
- `url` (str, nullable)
- `sentiment_score` (numeric(5,4), nullable) — -1.0 to +1.0
- `sentiment_label` (str, nullable) — 利好/利空/中性/重大事件
- `created_at` (datetime, server_default now)

Unique constraint: (ts_code, source, title, pub_date)

#### Scenario: Insert announcement
- **WHEN** a new announcement is crawled
- **THEN** a row SHALL be inserted with source, sentiment fields nullable until analyzed

#### Scenario: Duplicate announcement ignored
- **WHEN** the same announcement (same ts_code, source, title, pub_date) is crawled again
- **THEN** it SHALL be ignored (ON CONFLICT DO NOTHING)

### Requirement: sentiment_daily table
The system SHALL provide a `sentiment_daily` database table with the following columns:

- `id` (int, PK, autoincrement)
- `ts_code` (str, not null)
- `trade_date` (date, not null)
- `avg_sentiment` (numeric(5,4), nullable)
- `news_count` (int, default 0)
- `positive_count` (int, default 0)
- `negative_count` (int, default 0)
- `neutral_count` (int, default 0)
- `source_breakdown` (JSONB, nullable)
- `created_at` (datetime, server_default now)

Unique constraint: (ts_code, trade_date)

#### Scenario: Upsert daily sentiment
- **WHEN** daily aggregation runs for a stock on a date
- **THEN** it SHALL upsert the sentiment_daily row

### Requirement: Alembic migration
The system SHALL provide an Alembic migration that creates both tables.

#### Scenario: Migration upgrade
- **WHEN** `alembic upgrade head` is executed
- **THEN** both `announcements` and `sentiment_daily` tables SHALL be created

#### Scenario: Migration downgrade
- **WHEN** `alembic downgrade -1` is executed
- **THEN** both tables SHALL be dropped
