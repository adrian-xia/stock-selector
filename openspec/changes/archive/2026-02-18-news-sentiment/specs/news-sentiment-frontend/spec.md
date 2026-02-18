## ADDED Requirements

### Requirement: News dashboard page
The system SHALL provide a frontend page at route `/news` accessible from the sidebar navigation menu.

The page SHALL contain:
1. A news list section with date filter, stock code search, and source filter
2. A sentiment trend chart (ECharts line chart) showing sentiment over time for a selected stock
3. A daily sentiment summary table showing top stocks by news activity

#### Scenario: View news list
- **WHEN** user navigates to `/news`
- **THEN** it SHALL display the latest news with pagination

#### Scenario: Search by stock code
- **WHEN** user enters a stock code in the search box
- **THEN** the news list SHALL filter to show only that stock's news

#### Scenario: View sentiment trend
- **WHEN** user selects a stock code
- **THEN** the sentiment trend chart SHALL display the 30-day sentiment trend

### Requirement: Navigation menu entry
The sidebar navigation SHALL include a "新闻舆情" menu item with an appropriate icon, positioned after "参数优化".

#### Scenario: Navigate to news page
- **WHEN** user clicks "新闻舆情" in the sidebar
- **THEN** the browser SHALL navigate to `/news`
