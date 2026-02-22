import { useState } from 'react'
import {
  Button, Card, DatePicker, Form, InputNumber, message, Modal,
  Progress, Select, Space, Table, Tag, Tooltip,
} from 'antd'
import { PlayCircleOutlined, EyeOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  runOptimization,
  fetchOptimizationList,
  fetchOptimizationResult,
  fetchParamSpace,
} from '../../api/optimization'
import { fetchStrategyList } from '../../api/strategy'
import QueryErrorAlert from '../../components/common/QueryErrorAlert'
import type {
  OptimizationListItem,
  OptimizationResultItem,
  OptimizationResultResponse,
  ParamSpace,
} from '../../types/optimization'

const { RangePicker } = DatePicker

export default function OptimizationPage() {
  const [form] = Form.useForm()
  const [paramSpace, setParamSpace] = useState<ParamSpace>({})
  const [page, setPage] = useState(1)
  const [resultModal, setResultModal] = useState<OptimizationResultResponse | null>(null)
  const queryClient = useQueryClient()

  // 策略列表
  const strategiesQuery = useQuery({
    queryKey: ['strategy-list'],
    queryFn: () => fetchStrategyList(),
    staleTime: 60_000,
    select: (res: any) => (res.strategies ?? res).map((s: any) => ({
      name: s.name, display_name: s.display_name ?? s.name,
    })),
  })

  // 任务列表
  const tasksQuery = useQuery({
    queryKey: ['optimization-list', page],
    queryFn: () => fetchOptimizationList(page),
  })
  // 提交优化任务
  const submitMutation = useMutation({
    mutationFn: runOptimization,
    onSuccess: () => {
      message.success('优化任务已提交')
      setPage(1)
      queryClient.invalidateQueries({ queryKey: ['optimization-list'] })
    },
  })

  // 策略选择变化时加载参数空间
  const onStrategyChange = async (name: string) => {
    try {
      const res = await fetchParamSpace(name)
      setParamSpace(res.param_space)
      const psFields: Record<string, any> = {}
      for (const [key, spec] of Object.entries(res.param_space)) {
        psFields[`ps_${key}_min`] = spec.min
        psFields[`ps_${key}_max`] = spec.max
        psFields[`ps_${key}_step`] = spec.step
      }
      form.setFieldsValue(psFields)
    } catch {
      setParamSpace({})
    }
  }

  // 提交表单
  const onSubmit = (values: any) => {
    const ps: ParamSpace = {}
    for (const key of Object.keys(paramSpace)) {
      ps[key] = {
        type: paramSpace[key].type,
        min: values[`ps_${key}_min`],
        max: values[`ps_${key}_max`],
        step: values[`ps_${key}_step`],
      }
    }
    const [startDate, endDate] = values.dateRange
    submitMutation.mutate({
      strategy_name: values.strategy_name,
      algorithm: values.algorithm,
      param_space: ps,
      stock_codes: values.stock_codes.split(/[,，\s]+/).filter(Boolean),
      start_date: startDate.format('YYYY-MM-DD'),
      end_date: endDate.format('YYYY-MM-DD'),
      initial_capital: values.initial_capital ?? 1000000,
      top_n: values.top_n ?? 20,
    })
  }

  // 查看结果
  const onViewResult = async (taskId: number) => {
    const res = await fetchOptimizationResult(taskId)
    setResultModal(res)
  }

  const statusColor: Record<string, string> = {
    pending: 'default', running: 'processing', completed: 'success', failed: 'error',
  }
  const taskColumns: ColumnsType<OptimizationListItem> = [
    { title: 'ID', dataIndex: 'task_id', width: 60 },
    { title: '策略', dataIndex: 'strategy_name', width: 140 },
    { title: '算法', dataIndex: 'algorithm', width: 80,
      render: (v: string) => v === 'grid' ? '网格搜索' : '遗传算法' },
    { title: '状态', dataIndex: 'status', width: 100,
      render: (v: string) => <Tag color={statusColor[v]}>{v}</Tag> },
    { title: '进度', dataIndex: 'progress', width: 120,
      render: (v: number) => <Progress percent={v} size="small" /> },
    { title: '组合数', dataIndex: 'total_combinations', width: 80 },
    { title: '创建时间', dataIndex: 'created_at', width: 160 },
    { title: '操作', width: 80, render: (_: any, record: OptimizationListItem) => (
      <Tooltip title="查看结果">
        <Button
          type="link" icon={<EyeOutlined />} size="small"
          disabled={record.status !== 'completed'}
          onClick={() => onViewResult(record.task_id)}
        />
      </Tooltip>
    )},
  ]

  const resultColumns: ColumnsType<OptimizationResultItem> = [
    { title: '排名', dataIndex: 'rank', width: 60 },
    { title: '参数', dataIndex: 'params', width: 200,
      render: (v: Record<string, number>) => JSON.stringify(v) },
    { title: 'Sharpe', dataIndex: 'sharpe_ratio', width: 80,
      render: (v: number | null) => v?.toFixed(4) ?? '-' },
    { title: '年化收益', dataIndex: 'annual_return', width: 90,
      render: (v: number | null) => v != null ? `${(v * 100).toFixed(2)}%` : '-' },
    { title: '最大回撤', dataIndex: 'max_drawdown', width: 90,
      render: (v: number | null) => v != null ? `${(v * 100).toFixed(2)}%` : '-' },
    { title: '胜率', dataIndex: 'win_rate', width: 80,
      render: (v: number | null) => v != null ? `${(v * 100).toFixed(1)}%` : '-' },
    { title: '交易数', dataIndex: 'total_trades', width: 70 },
  ]

  const strategies = strategiesQuery.data ?? []
  return (
    <div>
      <Card title="参数优化" style={{ marginBottom: 16 }}>
        {strategiesQuery.error && (
          <QueryErrorAlert error={strategiesQuery.error} refetch={strategiesQuery.refetch} message="策略列表加载失败" />
        )}
        <Form form={form} layout="inline" onFinish={onSubmit}
          initialValues={{ algorithm: 'grid', initial_capital: 1000000, top_n: 20 }}
          style={{ flexWrap: 'wrap', gap: 8 }}
        >
          <Form.Item name="strategy_name" label="策略" rules={[{ required: true }]}>
            <Select style={{ width: 160 }} placeholder="选择策略" loading={strategiesQuery.isLoading}
              onChange={onStrategyChange}
              options={strategies.map((s: any) => ({ value: s.name, label: s.display_name }))}
            />
          </Form.Item>
          <Form.Item name="algorithm" label="算法">
            <Select style={{ width: 120 }}
              options={[
                { value: 'grid', label: '网格搜索' },
                { value: 'genetic', label: '遗传算法' },
              ]}
            />
          </Form.Item>
          <Form.Item name="stock_codes" label="股票代码" rules={[{ required: true }]}>
            <Select mode="tags" style={{ width: 240 }} placeholder="输入代码回车" />
          </Form.Item>
          <Form.Item name="dateRange" label="回测区间" rules={[{ required: true }]}>
            <RangePicker />
          </Form.Item>
          <Form.Item name="initial_capital" label="初始资金">
            <InputNumber min={10000} step={100000} style={{ width: 130 }} />
          </Form.Item>
          <Form.Item name="top_n" label="Top N">
            <InputNumber min={1} max={100} style={{ width: 80 }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={submitMutation.isPending}
              icon={<PlayCircleOutlined />}>
              开始优化
            </Button>
          </Form.Item>
        </Form>

        {/* 参数范围配置 */}
        {Object.keys(paramSpace).length > 0 && (
          <Card size="small" title="参数范围" style={{ marginTop: 12 }}>
            <Space wrap>
              {Object.entries(paramSpace).map(([key, spec]) => (
                <Space key={key} size="small">
                  <span style={{ fontWeight: 500 }}>{key}({spec.type}):</span>
                  <Form.Item name={`ps_${key}_min`} noStyle>
                    <InputNumber size="small" style={{ width: 80 }} placeholder="min" />
                  </Form.Item>
                  <span>~</span>
                  <Form.Item name={`ps_${key}_max`} noStyle>
                    <InputNumber size="small" style={{ width: 80 }} placeholder="max" />
                  </Form.Item>
                  <span>step:</span>
                  <Form.Item name={`ps_${key}_step`} noStyle>
                    <InputNumber size="small" style={{ width: 80 }} placeholder="step" />
                  </Form.Item>
                </Space>
              ))}
            </Space>
          </Card>
        )}
      </Card>

      <Card title="优化任务列表">
        {tasksQuery.error ? (
          <QueryErrorAlert error={tasksQuery.error} refetch={tasksQuery.refetch} />
        ) : (
          <Table
            rowKey="task_id"
            columns={taskColumns}
            dataSource={tasksQuery.data?.items ?? []}
            loading={tasksQuery.isLoading}
            pagination={{
              current: page, total: tasksQuery.data?.total ?? 0, pageSize: 20,
              onChange: (p) => setPage(p),
            }}
            size="small"
          />
        )}
      </Card>

      <Modal
        title={`优化结果 #${resultModal?.task_id ?? ''}`}
        open={!!resultModal}
        onCancel={() => setResultModal(null)}
        footer={null}
        width={900}
      >
        {resultModal && (
          <Table
            rowKey="rank"
            columns={resultColumns}
            dataSource={resultModal.results}
            pagination={false}
            size="small"
            scroll={{ y: 400 }}
          />
        )}
      </Modal>
    </div>
  )
}
