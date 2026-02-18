## ADDED Requirements

### Requirement: Get news list
The system SHALL provide `GET /api/v1/news/list` endpoint with pagination and filtering.

Query params: `page` (default 1), `page_size` (default 20), `ts_code` (optional), `source` (optional), `start_date` (optional), `end_date` (optional)

#### Scenario: List all news
- **WHEN** GET `/api/v1/news/list?page=1&page_size=20`
- **THEN** it SHALL return paginated announcements sorted by pub_date descending

#### Scenario: Filter by stock code
- **WHEN** GET `/api/v1/news/list?ts_code=600519.SH`
- **THEN** it SHALL return only announcements for that stock

### Requirement: Get sentiment trend
The system SHALL provide `GET /api/v1/news/sentiment-trend/{ts_code}` endpoint.

Query params: `days` (default 30)

Response: list of daily sentiment data points with trade_date, avg_sentiment, news_count, positive_count, negative_count.

#### Scenario: Query 30-day trend
- **WHEN** GET `/api/v1/news/sentiment-trend/600519.SH?days=30`
- **THEN** it SHALL return up to 30 daily sentiment data points sorted by trade_date ascending

#### Scenario: No data available
- **WHEN** no sentiment data exists for the stock
- **THEN** it SHALL return an empty list

### Requirement: Get stock sentiment summary
The system SHALL provide `GET /api/v1/news/sentiment-summary` endpoint.

Query params: `trade_date` (optional, defaults to latest), `top_n` (default 20)

Response: top N stocks by news_count with their sentiment metrics.

#### Scenario: Query daily summary
- **WHEN** GET `/api/v1/news/sentiment-summary?trade_date=2026-02-18`
- **THEN** it SHALL return top 20 stocks by news_count with avg_sentiment and counts
