## ADDED Requirements

### Requirement: 路由级懒加载
系统 SHALL 使用 React.lazy 对所有页面组件实现路由级懒加载，配合 Suspense 提供加载回退。

#### Scenario: 首次访问应用只加载当前页面
- **WHEN** 用户首次访问 /workbench
- **THEN** 浏览器 SHALL 只加载 workbench 页面的 chunk
- **AND** 其他页面（backtest、optimization、news、monitor）的代码 SHALL 不被加载

#### Scenario: 导航到新页面时按需加载
- **WHEN** 用户从 /workbench 导航到 /backtest
- **THEN** 浏览器 SHALL 按需加载 backtest 页面的 chunk
- **AND** 加载期间 SHALL 显示 PageLoading 组件

### Requirement: Vite 手动 chunk 分割
系统 SHALL 在 vite.config.ts 中配置 manualChunks，将第三方依赖分割为独立 chunk。

#### Scenario: 第三方库独立分割
- **WHEN** 执行 vite build
- **THEN** SHALL 生成以下独立 chunk：vendor-react（react/react-dom/react-router-dom）、vendor-antd（antd/@ant-design/icons）、vendor-echarts（echarts/echarts-for-react）
- **AND** 每个页面 SHALL 生成独立的 chunk 文件
