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

### Requirement: Taoguba sentiment crawler
The system SHALL provide a `TaogubaCrawler` class in `app/data/sources/taoguba.py` that fetches discussion sentiment data from Taoguba.

The crawler SHALL return dicts with: ts_code, title, summary, pub_date, url, source="taoguba"

#### Scenario: Fetch discussions for a stock
- **WHEN** `TaogubaCrawler.fetch(ts_codes=["600519.SH"], date=2026-02-18)` is called
- **THEN** it SHALL return a list of discussion dicts from Taoguba

#### Scenario: Crawler respects rate limits
- **WHEN** multiple requests are made
- **THEN** the crawler SHALL wait at least 1 second between requests

### Requirement: Xueqiu sentiment crawler
The system SHALL provide a `XueqiuCrawler` class in `app/data/sources/xueqiu.py` that fetches discussion data from Xueqiu.

The crawler SHALL return dicts with: ts_code, title, summary, pub_date, url, source="xueqiu"

#### Scenario: Fetch discussions for a stock
- **WHEN** `XueqiuCrawler.fetch(ts_codes=["600519.SH"], date=2026-02-18)` is called
- **THEN** it SHALL return a list of discussion dicts from Xueqiu

#### Scenario: Crawler handles empty results
- **WHEN** no discussions exist for the given stock and date
- **THEN** the crawler SHALL return an empty list without error

### Requirement: Unified news fetcher
The system SHALL provide a `fetch_all_news(ts_codes, date)` async function that calls all 3 crawlers in parallel and merges results.

#### Scenario: Parallel fetch from all sources
- **WHEN** `fetch_all_news(["600519.SH"], date)` is called
- **THEN** it SHALL call EastMoney, Taoguba, and Xueqiu crawlers concurrently and return merged results

#### Scenario: Partial source failure
- **WHEN** one crawler fails
- **THEN** results from other crawlers SHALL still be returned
