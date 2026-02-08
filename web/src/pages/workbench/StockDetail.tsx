import { Card, Descriptions, Tag, Typography, Empty } from 'antd'
import type { StockPick } from '../../types'

const { Paragraph } = Typography

interface Props {
  stock: StockPick | null
  aiEnabled: boolean
}

export default function StockDetail({ stock, aiEnabled }: Props) {
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
    </Card>
  )
}
