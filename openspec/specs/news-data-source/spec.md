## ADDED Requirements

### Requirement: EastMoney announcement crawler
The system SHALL provide an `EastMoneyCrawler` class in `app/data/sources/eastmoney.py` that fetches company announcements from East Money's public API.

The crawler SHALL:
- Accept a list of stock codes and a target date
- Return a list of announcement dicts with: ts_code, title, summary, pub_date, url, source="eastmoney"
- Implement request throttling (1-2 seconds between requests)
- Handle HTTP errors gracefully with retries (max 3)
- Respect a configurable timeout

#### Scenario: Fetch announcements for a stock
- **WHEN** `EastMoneyCrawler.fetch(ts_codes=["600519.SH"], date=2026-02-18)` is called
- **THEN** it SHALL return a list of announcement dicts from East Money for that date

#### Scenario: HTTP error handling
- **WHEN** East Money API returns a non-200 status
- **THEN** the crawler SHALL retry up to 3 times and return an empty list on failure

### Requirement: THS news crawler
The system SHALL provide a `THSCrawler` class in `app/data/sources/ths.py` that fetches stock news from 10jqka (同花顺) public API.

The crawler SHALL return dicts with: ts_code, title, summary, pub_date, url, source="ths"

#### Scenario: Fetch news for a stock
- **WHEN** `THSCrawler.fetch(ts_codes=["600519.SH"], date=2026-02-18)` is called
- **THEN** it SHALL return a list of news dicts from THS

#### Scenario: Crawler respects rate limits
- **WHEN** multiple requests are made
- **THEN** the crawler SHALL wait at least 1 second between requests

### Requirement: Sina 7x24 news crawler
The system SHALL provide a `SinaCrawler` class in `app/data/sources/sina.py` that fetches market-wide news from Sina 7x24 feed and matches them to stocks via local text matching.

The crawler SHALL:
- Accept a `stock_names` dict mapping ts_code to stock name
- Fetch the global news feed (not per-stock)
- Match news to stocks by 6-digit code or stock name (>=2 chars) in text
- Return dicts with: ts_code, title, summary, pub_date, url, source="sina"
- Clean HTML tags from rich_text content

#### Scenario: Match news by stock code
- **WHEN** a feed item contains "600519" in its text
- **THEN** it SHALL be matched to ts_code "600519.SH"

#### Scenario: Match news by stock name
- **WHEN** a feed item contains "贵州茅台" in its text
- **THEN** it SHALL be matched to ts_code "600519.SH"

#### Scenario: No match returns empty
- **WHEN** no feed items match the given stock codes
- **THEN** the crawler SHALL return an empty list

### Requirement: Unified news fetcher
The system SHALL provide a `fetch_all_news(ts_codes, date)` async function that calls all 3 crawlers in parallel and merges results.

The fetcher SHALL load stock names from the database for Sina crawler text matching, falling back to code-only matching on failure.

#### Scenario: Parallel fetch from all sources
- **WHEN** `fetch_all_news(["600519.SH"], date)` is called
- **THEN** it SHALL call EastMoney, Sina, and THS crawlers concurrently and return merged results

#### Scenario: Partial source failure
- **WHEN** one crawler fails
- **THEN** results from other crawlers SHALL still be returned
