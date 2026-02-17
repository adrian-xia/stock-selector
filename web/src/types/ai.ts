/** AI 分析结果类型定义 */

export interface AIAnalysisItem {
  ts_code: string
  trade_date: string
  ai_score: number
  ai_signal: string
  ai_summary: string
  prompt_version: string
  token_usage: Record<string, number> | null
  created_at: string | null
}

export interface AIAnalysisListResponse {
  trade_date: string
  total: number
  results: AIAnalysisItem[]
}
