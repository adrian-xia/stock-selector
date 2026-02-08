import apiClient from './client'
import type {
  BacktestRunRequest,
  BacktestRunResponse,
  BacktestResultResponse,
  BacktestListResponse,
} from '../types'

/** 执行回测 */
export async function runBacktest(req: BacktestRunRequest) {
  const { data } = await apiClient.post<BacktestRunResponse>('/backtest/run', req)
  return data
}

/** 查询回测结果详情 */
export async function fetchBacktestResult(taskId: number) {
  const { data } = await apiClient.get<BacktestResultResponse>(`/backtest/result/${taskId}`)
  return data
}

/** 查询回测任务列表 */
export async function fetchBacktestList(page = 1, pageSize = 20) {
  const { data } = await apiClient.get<BacktestListResponse>('/backtest/list', {
    params: { page, page_size: pageSize },
  })
  return data
}
