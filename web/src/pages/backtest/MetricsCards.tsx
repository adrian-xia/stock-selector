import { Card, Col, Row, Statistic } from 'antd'
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons'
import type { BacktestMetrics } from '../../types'

interface Props {
  metrics: BacktestMetrics
}

/** 格式化百分比 */
function pct(v: number | null): string {
  if (v == null) return '-'
  return `${(v * 100).toFixed(2)}%`
}

export default function MetricsCards({ metrics }: Props) {
  const annualReturn = metrics.annual_return ?? 0
  const isPositive = annualReturn >= 0

  return (
    <Row gutter={[16, 16]}>
      <Col span={4}>
        <Card size="small">
          <Statistic
            title="年化收益率"
            value={pct(metrics.annual_return)}
            valueStyle={{ color: isPositive ? '#cf1322' : '#3f8600' }}
            prefix={isPositive ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
          />
        </Card>
      </Col>
      <Col span={4}>
        <Card size="small">
          <Statistic
            title="最大回撤"
            value={pct(metrics.max_drawdown)}
            valueStyle={{ color: '#cf1322' }}
          />
        </Card>
      </Col>
      <Col span={4}>
        <Card size="small">
          <Statistic title="夏普比率" value={metrics.sharpe_ratio?.toFixed(2) ?? '-'} />
        </Card>
      </Col>
      <Col span={4}>
        <Card size="small">
          <Statistic title="胜率" value={pct(metrics.win_rate)} />
        </Card>
      </Col>
      <Col span={4}>
        <Card size="small">
          <Statistic title="总交易次数" value={metrics.total_trades} />
        </Card>
      </Col>
      <Col span={4}>
        <Card size="small">
          <Statistic title="盈亏比" value={metrics.profit_loss_ratio?.toFixed(2) ?? '-'} />
        </Card>
      </Col>
    </Row>
  )
}
