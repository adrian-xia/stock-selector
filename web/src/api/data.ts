import apiClient from './client'
import type { KlineResponse } from '../types'

/** 查询 K 线数据 */
export async function fetchKline(
  tsCode: string,
  options?: { startDate?: string; endDate?: string; limit?: number },
) {
  const { data } = await apiClient.get<KlineResponse>(`/data/kline/${tsCode}`, {
    params: {
      start_date: options?.startDate,
      end_date: options?.endDate,
      limit: options?.limit,
    },
  })
  return data
}
