## ADDED Requirements

### Requirement: News sentiment analyzer
The system SHALL provide a `NewsSentimentAnalyzer` class in `app/ai/news_analyzer.py` that uses Gemini Flash to analyze sentiment of news items.

The analyzer SHALL:
- Accept a list of news dicts (title, summary, ts_code)
- Call GeminiClient.chat_json() with a sentiment analysis prompt
- Return sentiment results: score (-1.0 to +1.0), label (利好/利空/中性/重大事件)
- Process news in batches (configurable batch_size, default 10)

#### Scenario: Analyze news sentiment
- **WHEN** `analyzer.analyze(news_items)` is called with a list of news
- **THEN** it SHALL return a list of dicts with ts_code, title, sentiment_score, sentiment_label

#### Scenario: Empty news list
- **WHEN** `analyzer.analyze([])` is called
- **THEN** it SHALL return an empty list without calling Gemini

#### Scenario: Gemini failure graceful degradation
- **WHEN** Gemini API call fails
- **THEN** the analyzer SHALL log a warning and return items with sentiment_score=0.0 and sentiment_label="中性"

### Requirement: Sentiment prompt template
The system SHALL provide a YAML prompt template at `app/ai/prompts/news_sentiment_v1.yaml` for news sentiment analysis.

The template SHALL instruct the model to:
- Analyze each news item's sentiment
- Return a score from -1.0 (极度负面) to +1.0 (极度正面)
- Classify as: 利好, 利空, 中性, 重大事件
- Return JSON array format

#### Scenario: Prompt template exists and is valid
- **WHEN** the prompt template is loaded
- **THEN** it SHALL contain system_prompt and user_prompt_template fields

### Requirement: Daily sentiment aggregation
The system SHALL provide an `aggregate_daily_sentiment(announcements, trade_date)` function that computes daily sentiment metrics per stock.

Metrics: avg_sentiment, news_count, positive_count (score > 0.2), negative_count (score < -0.2), neutral_count, source_breakdown (JSONB).

#### Scenario: Aggregate sentiment for a stock
- **WHEN** a stock has 5 news items with scores [0.8, 0.5, -0.3, 0.1, -0.7]
- **THEN** avg_sentiment SHALL be 0.08, positive_count=2, negative_count=2, neutral_count=1
