## Why

前端当前存在三大问题：(1) 加载/错误处理模式不统一，3 个页面绕过 React Query 使用原生 state，MonitorPage 完全静默失败；(2) 数据可视化能力不足，StockDetail 缺少 K 线图（`api/data.ts` 的 `fetchKline` 闲置），ECharts 配置内联无复用；(3) 无任何性能优化，路由无懒加载、无代码分割、Zustand 已安装但零使用。需要系统性提升用户体验和前端工程质量。

## What Changes

- 统一所有页面数据获取为 React Query，消除手动 useState/useEffect 模式（news、optimization、monitor 三个页面）
- 添加全局 ErrorBoundary 和 Suspense fallback，统一加载/错误 UI
- 路由级 React.lazy 懒加载 + Vite 手动 chunk 分割策略
- StockDetail 组件集成 K 线图（使用已有的 `api/data.ts` fetchKline）
- ECharts 公共配置抽取 + 主题定制
- MonitorPage 拆分子组件（当前 373 行单文件）
- 响应式布局优化（移动端适配关键页面）

## Capabilities

### New Capabilities
- `frontend-error-boundary`: 全局错误边界和统一加载状态组件
- `frontend-lazy-loading`: 路由懒加载和代码分割优化
- `frontend-kline-chart`: StockDetail K 线图可视化（分时图 + 技术指标叠加）
- `frontend-chart-theme`: ECharts 公共主题和配置复用层

### Modified Capabilities
- `workbench-page`: StockDetail 新增 K 线图展示，错误处理统一化
- `monitor-dashboard`: 组件拆分重构，React Query 统一数据获取，错误状态可见化
- `news-sentiment-frontend`: React Query 迁移，加载/错误 UI 统一化

## Impact

- **代码：** `web/src/` 全部页面和组件，新增 components/common 公共组件目录
- **API：** 无后端变更，复用已有 API（`api/data.ts` fetchKline 等）
- **依赖：** 无新增依赖，充分利用已安装的 React 19 Suspense、Zustand 5、React Query 5
- **构建：** vite.config.ts 新增 rollupOptions 手动 chunk 分割
