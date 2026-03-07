/** StarMap 投研 API 类型定义 */

export interface MacroSignal {
    risk_appetite: 'high' | 'mid' | 'low'
    global_risk_score: number
    summary: string
    positive_sectors: string[]
    negative_sectors: string[]
}

export interface SectorItem {
    sector_code: string
    sector_name: string
    news_score: number
    moneyflow_score: number
    trend_score: number
    final_score: number
    confidence: number
    drivers: string[]
}

export interface TradePlanItem {
    ts_code: string
    source_strategy: string
    plan_type: string
    plan_status: string
    valid_date: string | null
    direction: string
    trigger_price: number | null
    stop_loss_price: number | null
    take_profit_price: number | null
    risk_reward_ratio: number | null
    triggered: boolean | null
    actual_price: number | null
    entry_rule: string
    stop_loss_rule: string
    take_profit_rule: string
    emergency_exit_text: string
    position_suggestion: number
    market_regime: string
    market_risk_score: number
    sector_name: string
    sector_score: number | null
    confidence: number
    reasoning: string[]
    risk_flags: string[]
}

export interface ResearchOverview {
    trade_date: string
    macro_signal: MacroSignal
    top_sectors: SectorItem[]
    trade_plans: TradePlanItem[]
}
