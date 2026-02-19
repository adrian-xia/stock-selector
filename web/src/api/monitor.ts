/** 实时监控 & 告警 API */

import apiClient from './client'
import type {
  AlertRule,
  AlertRuleCreate,
  AlertRuleUpdate,
  AlertHistoryItem,
  RealtimeStatus,
} from '../types/monitor'

// --- 告警规则 ---

export async function fetchAlertRules() {
  const { data } = await apiClient.get<AlertRule[]>('/alerts/rules')
  return data
}

export async function createAlertRule(body: AlertRuleCreate) {
  const { data } = await apiClient.post<AlertRule>('/alerts/rules', body)
  return data
}

export async function updateAlertRule(ruleId: number, body: AlertRuleUpdate) {
  const { data } = await apiClient.put<AlertRule>(`/alerts/rules/${ruleId}`, body)
  return data
}

export async function deleteAlertRule(ruleId: number) {
  await apiClient.delete(`/alerts/rules/${ruleId}`)
}

// --- 告警历史 ---

export async function fetchAlertHistory(params?: {
  ts_code?: string
  start_date?: string
  end_date?: string
  page?: number
  page_size?: number
}) {
  const { data } = await apiClient.get<AlertHistoryItem[]>('/alerts/history', { params })
  return data
}

// --- 实时监控状态 ---

export async function fetchRealtimeStatus() {
  const { data } = await apiClient.get<RealtimeStatus>('/realtime/status')
  return data
}

export async function addWatchlist(tsCodes: string[]) {
  const { data } = await apiClient.post('/realtime/watchlist', { ts_codes: tsCodes })
  return data
}

export async function removeWatchlist(tsCodes: string[]) {
  const { data } = await apiClient.delete('/realtime/watchlist', { data: { ts_codes: tsCodes } })
  return data
}
