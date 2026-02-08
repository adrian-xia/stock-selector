import { Card, Form, Input, DatePicker, InputNumber, Button, Select, message } from 'antd'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useState } from 'react'
import dayjs from 'dayjs'
import { fetchStrategyList } from '../../api/strategy'
import { runBacktest } from '../../api/backtest'

const { RangePicker } = DatePicker

export default function BacktestNewPage() {
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const [submitting, setSubmitting] = useState(false)

  const { data: strategyData } = useQuery({
    queryKey: ['strategyList'],
    queryFn: () => fetchStrategyList(),
  })

  const strategyOptions = (strategyData?.strategies ?? []).map((s) => ({
    label: s.display_name,
    value: s.name,
  }))

  const handleSubmit = async (values: {
    strategy_name: string
    stock_codes: string
    date_range: [dayjs.Dayjs, dayjs.Dayjs]
    initial_capital: number
  }) => {
    const codes = values.stock_codes
      .split(/[,，\s]+/)
      .map((s) => s.trim())
      .filter(Boolean)

    if (codes.length === 0) {
      message.warning('请输入至少一个股票代码')
      return
    }

    setSubmitting(true)
    try {
      const res = await runBacktest({
        strategy_name: values.strategy_name,
        stock_codes: codes,
        start_date: values.date_range[0].format('YYYY-MM-DD'),
        end_date: values.date_range[1].format('YYYY-MM-DD'),
        initial_capital: values.initial_capital,
      })
      message.success('回测已提交')
      navigate(`/backtest/${res.task_id}`)
    } catch {
      // 错误已由 axios 拦截器处理
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div>
      <h2>新建回测</h2>
      <Card style={{ maxWidth: 600 }}>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{ initial_capital: 1000000 }}
        >
          <Form.Item
            name="strategy_name"
            label="策略"
            rules={[{ required: true, message: '请选择策略' }]}
          >
            <Select options={strategyOptions} placeholder="选择策略" />
          </Form.Item>

          <Form.Item
            name="stock_codes"
            label="股票代码"
            rules={[{ required: true, message: '请输入股票代码' }]}
            extra="多个代码用逗号分隔，如 600519.SH, 000001.SZ"
          >
            <Input.TextArea rows={2} placeholder="600519.SH, 000001.SZ" />
          </Form.Item>

          <Form.Item
            name="date_range"
            label="回测时间范围"
            rules={[{ required: true, message: '请选择时间范围' }]}
          >
            <RangePicker style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            name="initial_capital"
            label="初始资金（元）"
            rules={[{ required: true, message: '请输入初始资金' }]}
          >
            <InputNumber
              style={{ width: '100%' }}
              min={10000}
              step={100000}
              formatter={(v) => `${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
            />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={submitting} block>
              开始回测
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}
