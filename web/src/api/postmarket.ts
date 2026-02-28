import apiClient from './client'
import type {
  DailySummary,
  DailyPickDetail,
  PostMarketOverview,
  MarketOptRunRequest,
  MarketOptTask,
  MarketOptResultResponse,
} from '../types/postmarket'

/** 获取每日选股汇总 */
export async function fetchDailySummary(days = 30) {
  const { data } = await apiClient.get<DailySummary[]>('/strategy/picks/daily-summary', {
    params: { days },
  })
  return data
}

/** 获取指定日期选股明细 */
export async function fetchPicksByDate(pickDate: string) {
  const { data } = await apiClient.get<DailyPickDetail[]>('/strategy/picks/by-date', {
    params: { pick_date: pickDate },
  })
  return data
}

/** 获取盘后概览 */
export async function fetchPostMarketOverview(days = 7) {
  const { data } = await apiClient.get<PostMarketOverview>('/strategy/post-market/overview', {
    params: { days },
  })
  return data
}

/** 提交全市场优化任务 */
export async function runMarketOpt(req: MarketOptRunRequest) {
  const { data } = await apiClient.post<{ task_id: number; status: string }>('/optimization/market-opt/run', req)
  return data
}

/** 查询全市场优化结果 */
export async function fetchMarketOptResult(taskId: number) {
  const { data } = await apiClient.get<MarketOptResultResponse>(`/optimization/market-opt/result/${taskId}`)
  return data
}

/** 查询全市场优化任务列表 */
export async function fetchMarketOptList() {
  const { data } = await apiClient.get<MarketOptTask[]>('/optimization/market-opt/list')
  return data
}
