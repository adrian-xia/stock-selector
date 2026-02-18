## ADDED Requirements

### Requirement: News crawl scheduler step
The system SHALL add a step 3.9 in the post-market chain (`run_post_market_chain`) that:
1. Fetches news from all 3 sources for stocks in the latest strategy results
2. Runs sentiment analysis on fetched news
3. Aggregates and saves daily sentiment data

The step SHALL be controlled by `news_crawl_enabled` config flag.

#### Scenario: News crawl in post-market chain
- **WHEN** the post-market chain runs and `news_crawl_enabled=True`
- **THEN** step 3.9 SHALL fetch news, analyze sentiment, and save results

#### Scenario: News crawl disabled
- **WHEN** `news_crawl_enabled=False`
- **THEN** step 3.9 SHALL be skipped with a log message

#### Scenario: News crawl failure
- **WHEN** step 3.9 fails
- **THEN** it SHALL log the error and NOT block subsequent steps

### Requirement: News crawl configuration
The system SHALL support the following configuration items in `app/config.py`:

- `news_crawl_enabled: bool = True`
- `news_crawl_timeout: int = 30`
- `news_crawl_max_pages: int = 5`
- `news_sentiment_batch_size: int = 10`

#### Scenario: Configuration loaded from env
- **WHEN** `NEWS_CRAWL_ENABLED=false` is set in .env
- **THEN** `settings.news_crawl_enabled` SHALL be False
