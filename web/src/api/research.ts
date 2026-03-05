import apiClient from './client'
import type { ResearchOverview, SectorItem, TradePlanItem } from '../types/research'

/** 获取投研总览 */
export async function fetchResearchOverview(tradeDate: string) {
    const { data } = await apiClient.get<ResearchOverview>('/research/overview', {
        params: { trade_date: tradeDate },
    })
    return data
}

/** 获取行业共振排名 */
export async function fetchSectorResonance(tradeDate: string, limit = 20) {
    const { data } = await apiClient.get<{ sectors: SectorItem[] }>('/research/sectors', {
        params: { trade_date: tradeDate, limit },
    })
    return data.sectors
}

/** 获取交易计划 */
export async function fetchTradePlans(tradeDate: string, status?: string) {
    const { data } = await apiClient.get<{ plans: TradePlanItem[] }>('/research/plans', {
        params: { trade_date: tradeDate, ...(status ? { status } : {}) },
    })
    return data.plans
}
