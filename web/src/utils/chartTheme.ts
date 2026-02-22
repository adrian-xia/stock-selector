import type { EChartsOption } from 'echarts'

/** A 股涨跌颜色 */
export const COLORS = {
  up: '#ef4444',
  down: '#22c55e',
  primary: '#1890ff',
  secondary: '#91caff',
  ma5: '#ef4444',
  ma10: '#f59e0b',
  ma20: '#3b82f6',
} as const

/** 公共 tooltip 配置 */
const baseTooltip = {
  trigger: 'axis' as const,
  backgroundColor: 'rgba(255,255,255,0.96)',
  borderColor: '#e5e7eb',
  textStyle: { fontSize: 12 },
}

/** 公共 grid 配置 */
const baseGrid = {
  left: 60,
  right: 20,
  top: 40,
  bottom: 40,
}

/** 公共 legend 配置 */
const baseLegend = {
  textStyle: { fontSize: 12 },
}

/** 公共主题基础配置 */
export const chartTheme: Partial<EChartsOption> = {
  tooltip: baseTooltip,
  grid: baseGrid,
  legend: baseLegend,
}

/**
 * 将组件特定配置与公共主题深度合并。
 * 组件特定配置优先于公共主题配置。
 */
export function mergeChartOption(custom: EChartsOption): EChartsOption {
  return {
    tooltip: { ...baseTooltip, ...(custom.tooltip as object) },
    grid: { ...baseGrid, ...(custom.grid as object) },
    legend: { ...baseLegend, ...(custom.legend as object) },
    ...custom,
  }
}
