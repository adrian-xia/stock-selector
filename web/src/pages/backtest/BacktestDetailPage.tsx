import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Alert, Card, Spin, Tabs } from 'antd'
import { fetchBacktestResult } from '../../api/backtest'
import MetricsCards from './MetricsCards'
import EquityCurve from './EquityCurve'
import TradesTable from './TradesTable'

export default function BacktestDetailPage() {
  const { taskId } = useParams<{ taskId: string }>()
  const id = Number(taskId)

  const { data, isLoading, error } = useQuery({
    queryKey: ['backtestResult', id],
    queryFn: () => fetchBacktestResult(id),
    enabled: !isNaN(id),
    // 轮询：pending/running 状态每 3 秒刷新，完成后停止
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (status === 'pending' || status === 'running') return 3000
      return false
    },
  })

  if (isNaN(id)) {
    return <Alert type="error" message="无效的任务 ID" />
  }

  if (isLoading) {
    return <Spin tip="加载回测结果..." style={{ display: 'block', marginTop: 100 }} />
  }

  if (error) {
    return <Alert type="error" message="加载失败" description={String(error)} />
  }

  if (!data) {
    return <Alert type="warning" message="回测任务不存在" />
  }

  // 运行中状态
  if (data.status === 'pending' || data.status === 'running') {
    return (
      <Card>
        <Spin tip={`回测${data.status === 'pending' ? '等待中' : '运行中'}...`}>
          <div style={{ height: 200 }} />
        </Spin>
      </Card>
    )
  }

  // 失败状态
  if (data.status === 'failed') {
    return (
      <Alert
        type="error"
        message="回测失败"
        description={data.error_message ?? '未知错误'}
      />
    )
  }

  // 完成状态
  return (
    <div>
      <h2>回测结果 #{data.task_id}</h2>
      <p>
        策略: {data.strategy_name} | 股票: {data.stock_codes?.join(', ')} |
        时间: {data.start_date} ~ {data.end_date}
      </p>

      {data.result && <MetricsCards metrics={data.result} />}

      <Card style={{ marginTop: 16 }}>
        <Tabs
          items={[
            {
              key: 'curve',
              label: '收益曲线',
              children: <EquityCurve data={data.equity_curve ?? []} />,
            },
            {
              key: 'trades',
              label: '交易明细',
              children: <TradesTable trades={data.trades ?? []} />,
            },
          ]}
        />
      </Card>
    </div>
  )
}
