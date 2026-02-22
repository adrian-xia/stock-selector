import { Card, Descriptions, Tag, Typography, Empty, Spin } from 'antd'
import { useQuery } from '@tanstack/react-query'
import { fetchKline } from '../../api/data'
import KlineChart from '../../components/charts/KlineChart'
import type { StockPick } from '../../types'

const { Paragraph } = Typography

interface Props {
  stock: StockPick | null
  aiEnabled: boolean
}

export default function StockDetail({ stock, aiEnabled }: Props) {
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
        <Descriptions.Item label="匹配策略数">{stock.match_count}</Descriptions.Item>
      </Descriptions>

      <div style={{ marginTop: 8 }}>
        <strong>匹配策略：</strong>
        {stock.matched_strategies.map((s) => (
          <Tag key={s} style={{ marginTop: 4 }}>{s}</Tag>
        ))}
      </div>

      {aiEnabled && stock.ai_summary && (
        <div style={{ marginTop: 12 }}>
          <strong>AI 分析：</strong>
          {stock.ai_signal && (
            <Tag color={stock.ai_signal === 'BUY' ? 'red' : stock.ai_signal === 'SELL' ? 'green' : 'default'}>
              {stock.ai_signal} {stock.ai_score != null && `(${stock.ai_score}分)`}
            </Tag>
          )}
          <Paragraph style={{ marginTop: 4 }}>{stock.ai_summary}</Paragraph>
        </div>
      )}

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
