import apiClient from './client'
import type { StrategyConfig, StrategyConfigListResponse } from '../types/strategy'

/** 获取所有策略配置 */
export async function fetchStrategyConfigs(): Promise<StrategyConfig[]> {
  const { data } = await apiClient.get<StrategyConfigListResponse>('/strategy/config')
  return data.strategies
}

/** 更新单个策略配置 */
export async function updateStrategyConfig(
  name: string,
  payload: { is_enabled?: boolean; params?: Record<string, number> },
): Promise<StrategyConfig> {
  const { data } = await apiClient.put<StrategyConfig>(`/strategy/config/${name}`, payload)
  return data
}

/** 批量更新策略配置 */
export async function batchUpdateStrategyConfig(
  strategies: Array<{ name: string; is_enabled?: boolean; params?: Record<string, number> }>,
): Promise<{ updated: number }> {
  const { data } = await apiClient.put<{ updated: number }>('/strategy/config/batch', { strategies })
  return data
}
