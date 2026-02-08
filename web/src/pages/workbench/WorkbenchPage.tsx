import { useState, useCallback } from 'react'
import { Row, Col, Card, Button, Checkbox, message, Statistic, Space } from 'antd'
import { PlayCircleOutlined } from '@ant-design/icons'
import { runStrategy } from '../../api/strategy'
import StrategyPanel from './StrategyPanel'
import StrategyConfig from './StrategyConfig'
import ResultTable from './ResultTable'
import StockDetail from './StockDetail'
import type { StrategyMeta, StockPick, StrategyRunResponse } from '../../types'

interface SelectedStrategy {
  meta: StrategyMeta
  params: Record<string, number | string | boolean>
}

export default function WorkbenchPage() {
  // 策略选择状态
  const [selected, setSelected] = useState<Record<string, SelectedStrategy>>({})
  // 基础过滤
  const [excludeST, setExcludeST] = useState(true)
  const [excludeHalt, setExcludeHalt] = useState(true)
  // 执行状态
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<StrategyRunResponse | null>(null)
  // 详情
  const [selectedStock, setSelectedStock] = useState<StockPick | null>(null)

  const handleToggle = useCallback((name: string, meta: StrategyMeta) => {
    setSelected((prev) => {
      if (prev[name]) {
        const next = { ...prev }
        delete next[name]
        return next
      }
      return { ...prev, [name]: { meta, params: { ...meta.default_params } } }
    })
  }, [])

  const handleParamChange = useCallback((name: string, paramKey: string, value: number) => {
    setSelected((prev) => ({
      ...prev,
      [name]: {
        ...prev[name],
        params: { ...prev[name].params, [paramKey]: value },
      },
    }))
  }, [])

  const handleRemove = useCallback((name: string) => {
    setSelected((prev) => {
      const next = { ...prev }
      delete next[name]
      return next
    })
  }, [])

  /** PLACEHOLDER_WORKBENCH_CONTINUE */

  const handleRun = async () => {
    const names = Object.keys(selected)
    if (names.length === 0) {
      message.warning('请至少选择一个策略')
      return
    }

    setLoading(true)
    setSelectedStock(null)
    try {
      const res = await runStrategy({
        strategy_names: names,
        base_filter: { exclude_st: excludeST, exclude_halt: excludeHalt },
        top_n: 50,
      })
      setResult(res)
    } catch {
      // 错误已由 axios 拦截器处理
    } finally {
      setLoading(false)
    }
  }

  return (
    <Row gutter={16} style={{ height: '100%' }}>
      {/* 左侧：策略配置 */}
      <Col span={7}>
        <Card title="策略配置" size="small" style={{ marginBottom: 12 }}>
          <div style={{ marginBottom: 12 }}>
            <Checkbox checked={excludeST} onChange={(e) => setExcludeST(e.target.checked)}>
              剔除 ST
            </Checkbox>
            <Checkbox checked={excludeHalt} onChange={(e) => setExcludeHalt(e.target.checked)}>
              剔除停牌
            </Checkbox>
          </div>
          <StrategyPanel
            selected={Object.keys(selected)}
            onToggle={handleToggle}
          />
          <div style={{ marginTop: 12 }}>
            <StrategyConfig
              strategies={selected}
              onParamChange={handleParamChange}
              onRemove={handleRemove}
            />
          </div>
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            loading={loading}
            onClick={handleRun}
            block
            style={{ marginTop: 12 }}
          >
            运行筛选
          </Button>
        </Card>
      </Col>

      {/* 右侧：结果展示 */}
      <Col span={17}>
        {result && (
          <Space style={{ marginBottom: 12 }}>
            <Statistic title="筛选日期" value={result.target_date} />
            <Statistic title="结果数量" value={result.total_picks} />
            <Statistic title="耗时" value={result.elapsed_ms} suffix="ms" />
          </Space>
        )}
        <ResultTable
          picks={result?.picks ?? []}
          loading={loading}
          aiEnabled={result?.ai_enabled ?? false}
          onRowClick={setSelectedStock}
        />
        <div style={{ marginTop: 12 }}>
          <StockDetail
            stock={selectedStock}
            aiEnabled={result?.ai_enabled ?? false}
          />
        </div>
      </Col>
    </Row>
  )
}
