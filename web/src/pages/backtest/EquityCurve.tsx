import ReactECharts from 'echarts-for-react'
import { Empty } from 'antd'
import { mergeChartOption } from '../../utils/chartTheme'
import type { EquityCurveEntry } from '../../types'

interface Props {
  data: EquityCurveEntry[]
}

export default function EquityCurve({ data }: Props) {
  if (data.length === 0) {
    return <Empty description="暂无净值数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
  }

  const option = mergeChartOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params: unknown) => {
        const arr = params as Array<{ name: string; value: number }>
        const p = arr[0]
        return `${p.name}<br/>净值: ${p.value.toFixed(4)}`
      },
    },
    xAxis: {
      type: 'category',
      data: data.map((d) => d.date),
      axisLabel: { rotate: 30 },
    },
    yAxis: {
      type: 'value',
      name: '净值',
      scale: true,
    },
    series: [
      {
        type: 'line',
        data: data.map((d) => d.value),
        smooth: true,
        lineStyle: { width: 2 },
        areaStyle: { opacity: 0.1 },
      },
    ],
    grid: { left: 60, right: 20, top: 40, bottom: 60 },
  })

  return <ReactECharts option={option} style={{ height: 350 }} />
}
