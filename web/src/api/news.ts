import apiClient from './client'
import type {
  NewsListParams,
  NewsListResponse,
  SentimentTrendItem,
  SentimentSummaryResponse,
} from '../types/news'

/** 查询新闻列表（分页 + 筛选） */
export async function fetchNewsList(params: NewsListParams = {}) {
  const { data } = await apiClient.get<NewsListResponse>('/news/list', { params })
  return data
}

/** 查询指定股票的情感趋势 */
export async function fetchSentimentTrend(tsCode: string, days = 30) {
  const { data } = await apiClient.get<SentimentTrendItem[]>(
    `/news/sentiment-trend/${tsCode}`,
    { params: { days } },
  )
  return data
}

/** 查询每日情感摘要 */
export async function fetchSentimentSummary(tradeDate?: string, topN = 20) {
  const { data } = await apiClient.get<SentimentSummaryResponse>(
    '/news/sentiment-summary',
    { params: { trade_date: tradeDate, top_n: topN } },
  )
  return data
}
