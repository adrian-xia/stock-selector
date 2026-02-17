import apiClient from './client'
import type { AIAnalysisListResponse } from '../types'

/** 查询 AI 分析结果 */
export async function fetchAIAnalysis(date?: string) {
  const params = date ? { date } : {}
  const { data } = await apiClient.get<AIAnalysisListResponse>('/ai/analysis', { params })
  return data
}
