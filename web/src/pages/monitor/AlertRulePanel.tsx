/**
 * 告警规则管理子组件。
 */
import {
  Button, Card, Form, Input, InputNumber, Modal, Popconfirm, Select, Switch, Table, Tag,
} from 'antd'
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchAlertRules, createAlertRule, updateAlertRule, deleteAlertRule,
} from '../../api/monitor'
import QueryErrorAlert from '../../components/common/QueryErrorAlert'
import type { AlertRule } from '../../types/monitor'

export default function AlertRulePanel() {
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()
  const queryClient = useQueryClient()

  const rulesQuery = useQuery({
    queryKey: ['alert-rules'],
    queryFn: fetchAlertRules,
  })

  const createMutation = useMutation({
    mutationFn: createAlertRule,
    onSuccess: () => {
      setModalOpen(false)
      form.resetFields()
      queryClient.invalidateQueries({ queryKey: ['alert-rules'] })
    },
  })

  const toggleMutation = useMutation({
    mutationFn: (rule: AlertRule) => updateAlertRule(rule.id, { enabled: !rule.enabled }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['alert-rules'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteAlertRule,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['alert-rules'] }),
  })
  const handleCreate = async () => {
    const values = await form.validateFields()
    createMutation.mutate({
      ts_code: values.ts_code,
      rule_type: values.rule_type,
      params: values.rule_type === 'price_break'
        ? { target_price: values.target_price, direction: values.direction }
        : { signal_type: values.signal_type || '' },
      cooldown_minutes: values.cooldown_minutes ?? 30,
    })
  }

  const ruleColumns: ColumnsType<AlertRule> = [
    { title: '股票', dataIndex: 'ts_code', key: 'ts_code', width: 110 },
    {
      title: '类型', dataIndex: 'rule_type', key: 'rule_type', width: 100,
      render: (v: string) => v === 'price_break' ? <Tag color="blue">价格预警</Tag> : <Tag color="purple">策略信号</Tag>,
    },
    {
      title: '参数', dataIndex: 'params', key: 'params',
      render: (v: Record<string, unknown>) => JSON.stringify(v),
    },
    {
      title: '启用', key: 'enabled', width: 70,
      render: (_: unknown, r: AlertRule) => <Switch size="small" checked={r.enabled} onChange={() => toggleMutation.mutate(r)} />,
    },
    {
      title: '操作', key: 'action', width: 60,
      render: (_: unknown, r: AlertRule) => (
        <Popconfirm title="确认删除？" onConfirm={() => deleteMutation.mutate(r.id)}>
          <Button type="link" size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ]

  return (
    <>
      <Card
        title="告警规则"
        extra={<Button icon={<PlusOutlined />} size="small" onClick={() => setModalOpen(true)}>新建</Button>}
      >
        {rulesQuery.error ? (
          <QueryErrorAlert error={rulesQuery.error} refetch={rulesQuery.refetch} message="告警规则加载失败" />
        ) : (
          <Table columns={ruleColumns} dataSource={rulesQuery.data ?? []} rowKey="id" size="small"
            loading={rulesQuery.isLoading} pagination={false} />
        )}
      </Card>

      <Modal
        title="新建告警规则"
        open={modalOpen}
        onOk={handleCreate}
        confirmLoading={createMutation.isPending}
        onCancel={() => { setModalOpen(false); form.resetFields() }}
        destroyOnClose
      >
        <Form form={form} layout="vertical" initialValues={{ rule_type: 'price_break', direction: 'above', cooldown_minutes: 30 }}>
          <Form.Item name="ts_code" label="股票代码" rules={[{ required: true, message: '请输入股票代码' }]}>
            <Input placeholder="如 600519.SH" />
          </Form.Item>
          <Form.Item name="rule_type" label="规则类型" rules={[{ required: true }]}>
            <Select options={[
              { value: 'price_break', label: '价格预警' },
              { value: 'strategy_signal', label: '策略信号' },
            ]} />
          </Form.Item>
          <Form.Item noStyle shouldUpdate={(prev, cur) => prev.rule_type !== cur.rule_type}>
            {({ getFieldValue }) =>
              getFieldValue('rule_type') === 'price_break' ? (
                <>
                  <Form.Item name="target_price" label="目标价格" rules={[{ required: true, message: '请输入目标价格' }]}>
                    <InputNumber style={{ width: '100%' }} min={0} step={0.01} />
                  </Form.Item>
                  <Form.Item name="direction" label="方向">
                    <Select options={[
                      { value: 'above', label: '突破（>=）' },
                      { value: 'below', label: '跌破（<=）' },
                    ]} />
                  </Form.Item>
                </>
              ) : (
                <Form.Item name="signal_type" label="信号类型">
                  <Select allowClear placeholder="留空匹配所有信号" options={[
                    { value: 'ma_golden_cross', label: 'MA 金叉' },
                    { value: 'ma_death_cross', label: 'MA 死叉' },
                    { value: 'rsi_oversold', label: 'RSI 超卖' },
                    { value: 'rsi_overbought', label: 'RSI 超买' },
                  ]} />
                </Form.Item>
              )
            }
          </Form.Item>
          <Form.Item name="cooldown_minutes" label="冷却时间（分钟）">
            <InputNumber style={{ width: '100%' }} min={1} max={1440} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}
