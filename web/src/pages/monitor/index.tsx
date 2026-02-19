/**
 * 实时监控看板页面。
 *
 * 包含：自选股行情表格、自选股管理、告警历史、告警规则管理、连接状态。
 */
import { useCallback, useEffect, useState } from 'react'
import {
  Badge,
  Button,
  Card,
  Col,
  Input,
  Modal,
  notification,
  Popconfirm,
  Row,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Form,
  InputNumber,
} from 'antd'
import {
  DeleteOutlined,
  PlusOutlined,
  ReloadOutlined,
  WifiOutlined,
  DisconnectOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { useWebSocket, type ConnectionStatus, type RealtimeQuote } from '../../hooks/useWebSocket'
import {
  fetchRealtimeStatus,
  addWatchlist,
  removeWatchlist,
  fetchAlertRules,
  createAlertRule,
  updateAlertRule,
  deleteAlertRule,
  fetchAlertHistory,
} from '../../api/monitor'
import type { AlertRule, AlertHistoryItem } from '../../types/monitor'

/** 价格变动颜色 */
function priceColor(val?: number) {
  if (!val) return undefined
  return val > 0 ? '#cf1322' : val < 0 ? '#3f8600' : undefined
}

/** 连接状态 banner */
function StatusBanner({ status }: { status: ConnectionStatus }) {
  if (status === 'connected') return null
  return (
    <div
      style={{
        background: status === 'connecting' ? '#faad14' : '#ff4d4f',
        color: '#fff',
        textAlign: 'center',
        padding: '4px 0',
        fontSize: 13,
      }}
    >
      {status === 'connecting' ? '正在连接...' : '连接断开，5 秒后自动重连'}
    </div>
  )
}

export default function MonitorPage() {
  const { status, quotes, connect, disconnect, subscribe, unsubscribe } = useWebSocket()

  // 自选股
  const [watchlist, setWatchlist] = useState<string[]>([])
  const [addCode, setAddCode] = useState('')
  const [maxStocks, setMaxStocks] = useState(50)

  // 告警
  const [rules, setRules] = useState<AlertRule[]>([])
  const [history, setHistory] = useState<AlertHistoryItem[]>([])
  const [ruleModalOpen, setRuleModalOpen] = useState(false)
  const [ruleForm] = Form.useForm()

  // 上一次告警 ID，用于弹窗新告警
  const [lastAlertId, setLastAlertId] = useState(0)

  // --- 数据加载 ---
  const loadStatus = useCallback(async () => {
    try {
      const s = await fetchRealtimeStatus()
      setWatchlist(s.watchlist)
      setMaxStocks(s.max_stocks)
    } catch { /* ignore */ }
  }, [])

  const loadRules = useCallback(async () => {
    try {
      setRules(await fetchAlertRules())
    } catch { /* ignore */ }
  }, [])

  const loadHistory = useCallback(async () => {
    try {
      const items = await fetchAlertHistory({ page_size: 20 })
      setHistory(items)
      // 新告警弹窗
      if (items.length > 0 && items[0].id > lastAlertId) {
        if (lastAlertId > 0) {
          notification.warning({ message: '新告警', description: items[0].message, duration: 5 })
        }
        setLastAlertId(items[0].id)
      }
    } catch { /* ignore */ }
  }, [lastAlertId])

  // 初始化
  useEffect(() => {
    connect()
    loadStatus()
    loadRules()
    loadHistory()
    const timer = setInterval(loadHistory, 30000)
    return () => {
      disconnect()
      clearInterval(timer)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // 订阅自选股
  useEffect(() => {
    if (status === 'connected' && watchlist.length > 0) {
      subscribe(watchlist)
    }
  }, [status, watchlist, subscribe])

  // --- 自选股管理 ---
  const handleAdd = async () => {
    const code = addCode.trim().toUpperCase()
    if (!code) return
    try {
      await addWatchlist([code])
      subscribe([code])
      setAddCode('')
      await loadStatus()
    } catch { /* ignore */ }
  }

  const handleRemove = async (code: string) => {
    try {
      await removeWatchlist([code])
      unsubscribe([code])
      await loadStatus()
    } catch { /* ignore */ }
  }

  // --- 告警规则 ---
  const handleCreateRule = async () => {
    try {
      const values = await ruleForm.validateFields()
      await createAlertRule({
        ts_code: values.ts_code,
        rule_type: values.rule_type,
        params: values.rule_type === 'price_break'
          ? { target_price: values.target_price, direction: values.direction }
          : { signal_type: values.signal_type || '' },
        cooldown_minutes: values.cooldown_minutes ?? 30,
      })
      setRuleModalOpen(false)
      ruleForm.resetFields()
      await loadRules()
    } catch { /* ignore */ }
  }

  const handleToggleRule = async (rule: AlertRule) => {
    await updateAlertRule(rule.id, { enabled: !rule.enabled })
    await loadRules()
  }

  const handleDeleteRule = async (id: number) => {
    await deleteAlertRule(id)
    await loadRules()
  }

  // --- 行情表格列定义 ---
  const quoteColumns: ColumnsType<RealtimeQuote> = [
    { title: '代码', dataIndex: 'ts_code', key: 'ts_code', width: 110 },
    {
      title: '最新价', dataIndex: 'close', key: 'close', width: 90,
      render: (v: number, r: RealtimeQuote) => (
        <span style={{ color: priceColor(r.pct_chg), fontWeight: 600 }}>{v?.toFixed(2) ?? '-'}</span>
      ),
    },
    {
      title: '涨跌幅', dataIndex: 'pct_chg', key: 'pct_chg', width: 90,
      render: (v: number) => (
        <span style={{ color: priceColor(v) }}>{v != null ? `${v > 0 ? '+' : ''}${v.toFixed(2)}%` : '-'}</span>
      ),
    },
    { title: '开盘', dataIndex: 'open', key: 'open', width: 80, render: (v: number) => v?.toFixed(2) ?? '-' },
    { title: '最高', dataIndex: 'high', key: 'high', width: 80, render: (v: number) => v?.toFixed(2) ?? '-' },
    { title: '最低', dataIndex: 'low', key: 'low', width: 80, render: (v: number) => v?.toFixed(2) ?? '-' },
    { title: '成交量', dataIndex: 'vol', key: 'vol', width: 100, render: (v: number) => v != null ? `${(v / 100).toFixed(0)}手` : '-' },
    {
      title: '操作', key: 'action', width: 60,
      render: (_: unknown, r: RealtimeQuote) => (
        <Popconfirm title="确认移除？" onConfirm={() => handleRemove(r.ts_code)}>
          <Button type="link" size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ]

  // 构建行情数据源
  const quoteData: RealtimeQuote[] = watchlist.map((code) => {
    const q = quotes.get(code)
    return q ?? { ts_code: code }
  })

  // --- 告警规则列定义 ---
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
      render: (_: unknown, r: AlertRule) => <Switch size="small" checked={r.enabled} onChange={() => handleToggleRule(r)} />,
    },
    {
      title: '操作', key: 'action', width: 60,
      render: (_: unknown, r: AlertRule) => (
        <Popconfirm title="确认删除？" onConfirm={() => handleDeleteRule(r.id)}>
          <Button type="link" size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ]

  // --- 告警历史列定义 ---
  const historyColumns: ColumnsType<AlertHistoryItem> = [
    { title: '时间', dataIndex: 'triggered_at', key: 'triggered_at', width: 170 },
    { title: '股票', dataIndex: 'ts_code', key: 'ts_code', width: 110 },
    {
      title: '类型', dataIndex: 'rule_type', key: 'rule_type', width: 100,
      render: (v: string) => v === 'price_break' ? <Tag color="blue">价格</Tag> : <Tag color="purple">信号</Tag>,
    },
    { title: '消息', dataIndex: 'message', key: 'message' },
    {
      title: '通知', dataIndex: 'notified', key: 'notified', width: 60,
      render: (v: boolean) => v ? <Badge status="success" text="已发" /> : <Badge status="default" text="未发" />,
    },
  ]

  // --- 渲染 ---
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <StatusBanner status={status} />

      {/* 自选股行情 */}
      <Card
        title={
          <Space>
            <span>自选股行情</span>
            {status === 'connected'
              ? <Badge status="success" text={<span style={{ fontSize: 12 }}><WifiOutlined /> 已连接</span>} />
              : <Badge status="error" text={<span style={{ fontSize: 12 }}><DisconnectOutlined /> 未连接</span>} />}
          </Space>
        }
        extra={
          <Space>
            <Input
              placeholder="输入股票代码（如 600519.SH）"
              value={addCode}
              onChange={(e) => setAddCode(e.target.value)}
              onPressEnter={handleAdd}
              style={{ width: 220 }}
              disabled={watchlist.length >= maxStocks}
            />
            <Button icon={<PlusOutlined />} onClick={handleAdd} disabled={watchlist.length >= maxStocks}>
              添加
            </Button>
            <span style={{ fontSize: 12, color: '#999' }}>{watchlist.length}/{maxStocks}</span>
          </Space>
        }
      >
        <Table
          columns={quoteColumns}
          dataSource={quoteData}
          rowKey="ts_code"
          size="small"
          pagination={false}
          locale={{ emptyText: '暂无自选股，请添加股票代码' }}
        />
      </Card>

      {/* 告警规则 & 告警历史 */}
      <Row gutter={16}>
        <Col span={10}>
          <Card
            title="告警规则"
            extra={<Button icon={<PlusOutlined />} size="small" onClick={() => setRuleModalOpen(true)}>新建</Button>}
          >
            <Table columns={ruleColumns} dataSource={rules} rowKey="id" size="small" pagination={false} />
          </Card>
        </Col>
        <Col span={14}>
          <Card
            title="告警历史（最近 20 条）"
            extra={<Button icon={<ReloadOutlined />} size="small" onClick={loadHistory}>刷新</Button>}
          >
            <Table columns={historyColumns} dataSource={history} rowKey="id" size="small" pagination={false} />
          </Card>
        </Col>
      </Row>

      {/* 新建告警规则 Modal */}
      <Modal
        title="新建告警规则"
        open={ruleModalOpen}
        onOk={handleCreateRule}
        onCancel={() => { setRuleModalOpen(false); ruleForm.resetFields() }}
        destroyOnClose
      >
        <Form form={ruleForm} layout="vertical" initialValues={{ rule_type: 'price_break', direction: 'above', cooldown_minutes: 30 }}>
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
    </div>
  )
}
