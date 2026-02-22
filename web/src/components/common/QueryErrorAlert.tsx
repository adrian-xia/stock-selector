import { Alert, Button } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'

interface Props {
  error: Error | null
  refetch: () => void
  message?: string
}

/**
 * React Query error 状态统一展示组件。
 * 显示错误信息和重试按钮。
 */
export default function QueryErrorAlert({ error, refetch, message: msg }: Props) {
  return (
    <Alert
      type="error"
      showIcon
      message={msg || '数据加载失败'}
      description={error?.message || '请稍后重试'}
      action={
        <Button size="small" icon={<ReloadOutlined />} onClick={refetch}>
          重试
        </Button>
      }
      style={{ marginBottom: 16 }}
    />
  )
}
