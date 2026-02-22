## 1. 公共组件和基础设施

- [x] 1.1 创建 `web/src/components/common/ErrorBoundary.tsx`：React ErrorBoundary 类组件，捕获子组件错误，显示错误回退 UI（错误描述 + 重试按钮），路由切换时自动重置
- [x] 1.2 创建 `web/src/components/common/PageLoading.tsx`：页面级加载占位组件（居中 Spin + 提示文字）
- [x] 1.3 创建 `web/src/components/common/QueryErrorAlert.tsx`：React Query error 状态统一展示组件（Alert + 错误信息 + 重试按钮，接收 error 和 refetch props）
- [x] 1.4 创建 `web/src/utils/chartTheme.ts`：ECharts 公共主题配置（颜色方案、涨红跌绿、tooltip/legend/grid 样式）+ mergeChartOption 工具函数

## 2. 路由懒加载和代码分割

- [x] 2.1 修改 `web/src/App.tsx`：将 5 个页面组件改为 React.lazy 动态导入，用 Suspense + PageLoading 包裹，外层包裹 ErrorBoundary
- [x] 2.2 修改 `web/vite.config.ts`：添加 build.rollupOptions.output.manualChunks 配置，分割 vendor-react、vendor-antd、vendor-echarts

## 3. K 线图组件

- [x] 3.1 创建 `web/src/components/charts/KlineChart.tsx`：基于 ECharts candlestick 的 K 线图组件（K 线主图 + 成交量副图 + MA5/MA10/MA20 均线 + dataZoom 缩放），使用 chartTheme 公共配置
- [x] 3.2 修改 `web/src/pages/workbench/StockDetail.tsx`：集成 KlineChart 组件，通过 React Query + fetchKline 加载最近 120 个交易日数据，加载中显示 Spin

## 4. 现有图表迁移到公共主题

- [x] 4.1 修改 `web/src/pages/backtest/EquityCurve.tsx`：使用 chartTheme 的 mergeChartOption 替代内联配置
- [x] 4.2 修改 `web/src/pages/news/index.tsx` 中的情感趋势图：使用 chartTheme 的 mergeChartOption 替代内联配置

## 5. News 页面 React Query 迁移

- [x] 5.1 重构 `web/src/pages/news/index.tsx`：将新闻列表、情感趋势、每日摘要三个数据获取从 useState/useEffect 迁移到 React Query useQuery，移除手动 loading/state 管理
- [x] 5.2 在 news 页面集成 QueryErrorAlert 组件处理 API 错误

## 6. Optimization 页面 React Query 迁移

- [x] 6.1 重构 `web/src/pages/optimization/index.tsx`：将任务列表、策略列表、结果查询从 useState/useEffect 迁移到 React Query useQuery/useMutation，移除手动 loading/state 管理
- [x] 6.2 在 optimization 页面集成 QueryErrorAlert 组件处理 API 错误

## 7. Monitor 页面重构

- [x] 7.1 拆分 `web/src/pages/monitor/index.tsx` 为子组件：`WatchlistTable.tsx`（自选股行情表格）、`AlertRulePanel.tsx`（告警规则管理）、`AlertHistoryPanel.tsx`（告警历史），主页面组合子组件
- [x] 7.2 将 monitor 子组件的 API 数据获取迁移到 React Query（告警规则 useQuery、告警历史 useQuery + refetchInterval:30000、自选股 useQuery + useMutation）
- [x] 7.3 在 monitor 子组件集成 QueryErrorAlert，消除所有空 catch 静默失败

## 8. 文档更新

- [x] 8.1 更新 `README.md`：新增前端优化相关描述（ErrorBoundary、懒加载、K 线图、React Query 统一）
- [x] 8.2 更新 `CLAUDE.md`：更新目录结构（新增 components/common、components/charts、utils）
- [x] 8.3 更新 `PROJECT_TASKS.md`：标记 Change 15 frontend-enhancement 为已完成
