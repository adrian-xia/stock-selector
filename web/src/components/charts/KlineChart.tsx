import ReactECharts from 'echarts-for-react'
import { Empty } from 'antd'
import { mergeChartOption, COLORS } from '../../utils/chartTheme'
import type { KlineEntry } from '../../types/data'

interface Props {
  data: KlineEntry[]
  style?: React.CSSProperties
}

/** 计算移动平均线 */
function calcMA(data: KlineEntry[], period: number): (number | null)[] {
  return data.map((_, i) => {
    if (i < period - 1) return null
    let sum = 0
    for (let j = i - period + 1; j <= i; j++) sum += data[j].close
    return +(sum / period).toFixed(2)
  })
}

/**
 * K 线图组件。
 * 包含蜡烛图主图 + 成交量副图 + MA5/MA10/MA20 均线。
 */
export default function KlineChart({ data, style }: Props) {
  if (data.length === 0) {
    return <Empty description="暂无 K 线数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
  }

  const dates = data.map((d) => d.date)
  const ohlc = data.map((d) => [d.open, d.close, d.low, d.high])
  const volumes = data.map((d) => d.volume)
  const ma5 = calcMA(data, 5)
  const ma10 = calcMA(data, 10)
  const ma20 = calcMA(data, 20)

  // 成交量颜色：涨红跌绿
  const volColors = data.map((d) => (d.close >= d.open ? COLORS.up : COLORS.down))

  const option = mergeChartOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
    },
    legend: { data: ['K线', 'MA5', 'MA10', 'MA20'] },
    grid: [
      { left: 60, right: 20, top: 40, height: '55%' },
      { left: 60, right: 20, top: '75%', height: '15%' },
    ],
    xAxis: [
      { type: 'category', data: dates, gridIndex: 0, axisLabel: { show: false } },
      { type: 'category', data: dates, gridIndex: 1, axisLabel: { rotate: 30, fontSize: 10 } },
    ],
    yAxis: [
      { type: 'value', gridIndex: 0, scale: true, splitNumber: 4 },
      { type: 'value', gridIndex: 1, scale: true, splitNumber: 2, axisLabel: { show: false } },
    ],
    dataZoom: [
      { type: 'inside', xAxisIndex: [0, 1], start: 60, end: 100 },
      { type: 'slider', xAxisIndex: [0, 1], bottom: 5, height: 20, start: 60, end: 100 },
    ],
    series: [
      {
        name: 'K线',
        type: 'candlestick',
        data: ohlc,
        xAxisIndex: 0,
        yAxisIndex: 0,
        itemStyle: {
          color: COLORS.up,
          color0: COLORS.down,
          borderColor: COLORS.up,
          borderColor0: COLORS.down,
        },
      },
      { name: 'MA5', type: 'line', data: ma5, smooth: true, lineStyle: { width: 1 }, symbol: 'none', itemStyle: { color: COLORS.ma5 }, xAxisIndex: 0, yAxisIndex: 0 },
      { name: 'MA10', type: 'line', data: ma10, smooth: true, lineStyle: { width: 1 }, symbol: 'none', itemStyle: { color: COLORS.ma10 }, xAxisIndex: 0, yAxisIndex: 0 },
      { name: 'MA20', type: 'line', data: ma20, smooth: true, lineStyle: { width: 1 }, symbol: 'none', itemStyle: { color: COLORS.ma20 }, xAxisIndex: 0, yAxisIndex: 0 },
      {
        name: '成交量',
        type: 'bar',
        data: volumes.map((v, i) => ({ value: v, itemStyle: { color: volColors[i] } })),
        xAxisIndex: 1,
        yAxisIndex: 1,
      },
    ],
  })

  return <ReactECharts option={option} style={{ height: 420, ...style }} />
}
