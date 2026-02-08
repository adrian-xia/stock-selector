import { Card, InputNumber, Button, Empty } from 'antd'
import { CloseOutlined } from '@ant-design/icons'
import type { StrategyMeta } from '../../types'

interface SelectedStrategy {
  meta: StrategyMeta
  params: Record<string, number | string | boolean>
}

interface Props {
  strategies: Record<string, SelectedStrategy>
  onParamChange: (name: string, paramKey: string, value: number) => void
  onRemove: (name: string) => void
}

export default function StrategyConfig({ strategies, onParamChange, onRemove }: Props) {
  const entries = Object.entries(strategies)

  if (entries.length === 0) {
    return <Empty description="请从左侧选择策略" image={Empty.PRESENTED_IMAGE_SIMPLE} />
  }

  return (
    <div>
      {entries.map(([name, { meta, params }]) => (
        <Card
          key={name}
          title={meta.display_name}
          size="small"
          style={{ marginBottom: 8 }}
          extra={
            <Button
              type="text"
              size="small"
              icon={<CloseOutlined />}
              onClick={() => onRemove(name)}
            />
          }
        >
          {Object.entries(params).map(([paramKey, paramValue]) => (
            <div key={paramKey} style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
              <span style={{ width: 80, fontSize: 13 }}>{paramKey}:</span>
              <InputNumber
                size="small"
                value={paramValue as number}
                onChange={(val) => val !== null && onParamChange(name, paramKey, val)}
              />
            </div>
          ))}
        </Card>
      ))}
    </div>
  )
}
