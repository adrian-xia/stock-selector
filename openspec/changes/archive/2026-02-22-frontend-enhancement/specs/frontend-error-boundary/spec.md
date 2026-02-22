## ADDED Requirements

### Requirement: 全局错误边界组件
系统 SHALL 提供 React ErrorBoundary 组件，捕获子组件树中的 JavaScript 错误，显示友好的错误回退 UI。

#### Scenario: 页面组件抛出运行时错误
- **WHEN** 某个页面组件抛出未捕获的 JavaScript 错误
- **THEN** ErrorBoundary SHALL 捕获错误并显示错误回退页面
- **AND** 回退页面 SHALL 包含错误描述和"重试"按钮
- **AND** 点击"重试"SHALL 重置错误状态并重新渲染子组件

#### Scenario: 错误不影响其他页面
- **WHEN** workbench 页面发生错误
- **THEN** 用户导航到其他页面 SHALL 正常工作
- **AND** ErrorBoundary SHALL 在路由切换时自动重置

### Requirement: 统一加载状态组件
系统 SHALL 提供 PageLoading 组件作为页面级加载占位符。

#### Scenario: 页面懒加载时显示加载状态
- **WHEN** 用户导航到尚未加载的页面
- **THEN** SHALL 显示 PageLoading 组件（居中 Spin + 提示文字）
- **AND** 页面加载完成后 SHALL 自动替换为实际内容

### Requirement: 统一 API 错误展示组件
系统 SHALL 提供 QueryErrorAlert 组件，用于 React Query error 状态的统一展示。

#### Scenario: API 请求失败时显示错误提示
- **WHEN** React Query 请求返回错误
- **THEN** SHALL 显示 Alert 组件，包含错误信息和"重试"按钮
- **AND** 点击"重试"SHALL 触发 React Query refetch
