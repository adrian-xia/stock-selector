/** 新闻舆情相关类型定义 */

export interface AnnouncementItem {
  id: number
  ts_code: string
  title: string
  summary: string | null
  source: string
  pub_date: string
  url: string | null
  sentiment_score: number | null
  sentiment_label: string | null
}

export interface NewsListResponse {
  total: number
  page: number
  page_size: number
  items: AnnouncementItem[]
}

export interface NewsListParams {
  page?: number
  page_size?: number
  ts_code?: string
  source?: string
  start_date?: string
  end_date?: string
}

export interface SentimentTrendItem {
  trade_date: string
  avg_sentiment: number
  news_count: number
  positive_count: number
  negative_count: number
  neutral_count: number
}

export interface SentimentSummaryItem {
  ts_code: string
  avg_sentiment: number
  news_count: number
  positive_count: number
  negative_count: number
  neutral_count: number
  source_breakdown: Record<string, number> | null
}

export interface SentimentSummaryResponse {
  trade_date: string | null
  items: SentimentSummaryItem[]
}
