import { Card, Descriptions, Tag, Empty, Spin } from 'antd'
import { useQuery } from '@tanstack/react-query'
import { fetchKline } from '../../api/data'
import KlineChart from '../../components/charts/KlineChart'
import type { StockPick } from '../../types'

interface Props {
  stock: StockPick | null
}

export default function StockDetail({ stock }: Props) {
  // K 线数据查询（仅在选中股票时请求）
  const { data: klineData, isLoading: klineLoading } = useQuery({
    queryKey: ['kline', stock?.ts_code],
    queryFn: () => fetchKline(stock!.ts_code, { limit: 120 }),
    enabled: !!stock,
    staleTime: 60_000,
  })

  if (!stock) {
    return <Empty description="点击表格中的股票查看详情" image={Empty.PRESENTED_IMAGE_SIMPLE} />
  }

  return (
    <Card title={`${stock.name} (${stock.ts_code})`} size="small">
      <Descriptions column={3} size="small">
        <Descriptions.Item label="现价">{stock.close.toFixed(2)}</Descriptions.Item>
        <Descriptions.Item label="涨跌幅">
          <span style={{ color: stock.pct_chg >= 0 ? '#cf1322' : '#3f8600' }}>
            {stock.pct_chg >= 0 ? '+' : ''}{stock.pct_chg.toFixed(2)}%
          </span>
        </Descriptions.Item>
        <Descriptions.Item label="触发数">{stock.match_count}</Descriptions.Item>
        <Descriptions.Item label="质量分">{stock.quality_score.toFixed(1)}</Descriptions.Item>
        <Descriptions.Item label="综合分">{stock.final_score.toFixed(3)}</Descriptions.Item>
        <Descriptions.Item label="市场状态">{stock.market_regime}</Descriptions.Item>
        <Descriptions.Item label="确认加分">{stock.confirmed_bonus.toFixed(2)}</Descriptions.Item>
        <Descriptions.Item label="动态权重">{stock.dynamic_weight.toFixed(2)}</Descriptions.Item>
        <Descriptions.Item label="风格增益">{stock.style_bonus.toFixed(2)}</Descriptions.Item>
      </Descriptions>

      <div style={{ marginTop: 8 }}>
        <strong>风格标签：</strong>
        {Object.entries(stock.tags ?? {}).map(([key, value]) => (
          <Tag key={key} style={{ marginTop: 4 }}>{key}:{value.toFixed(2)}</Tag>
        ))}
      </div>

      <div style={{ marginTop: 12 }}>
        <strong>触发信号：</strong>
        {stock.triggered_signals.map((signal) => (
          <Tag key={signal.strategy} color="blue" style={{ marginTop: 4 }}>
            {signal.group} · {signal.strategy} · c={signal.confidence.toFixed(2)} · w={signal.weight.toFixed(2)}
          </Tag>
        ))}
      </div>

      {/* K 线走势图 */}
      <div style={{ marginTop: 12 }}>
        <strong>K 线走势：</strong>
        {klineLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}><Spin tip="加载 K 线数据..." /></div>
        ) : (
          <KlineChart data={klineData?.data ?? []} />
        )}
      </div>
    </Card>
  )
}
