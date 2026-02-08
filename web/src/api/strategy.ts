import apiClient from './client'
import type {
  StrategyListResponse,
  StrategySchemaResponse,
  StrategyRunRequest,
  StrategyRunResponse,
} from '../types'

/** 获取可用策略列表 */
export async function fetchStrategyList(category?: string) {
  const params = category ? { category } : {}
  const { data } = await apiClient.get<StrategyListResponse>('/strategy/list', { params })
  return data
}

/** 获取策略参数 schema */
export async function fetchStrategySchema(name: string) {
  const { data } = await apiClient.get<StrategySchemaResponse>(`/strategy/schema/${name}`)
  return data
}

/** 执行选股策略 */
export async function runStrategy(req: StrategyRunRequest) {
  const { data } = await apiClient.post<StrategyRunResponse>('/strategy/run', req)
  return data
}
