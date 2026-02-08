## 1. 后端 API 补充

- [x] 1.1 实现 K 线数据查询接口 `GET /api/v1/data/kline/{ts_code}`（app/api/data.py），支持 start_date、end_date、limit 参数，从 stock_daily 表查询 OHLCV 数据
- [x] 1.2 实现回测任务列表接口 `GET /api/v1/backtest/list`（app/api/backtest.py），分页查询 backtest_tasks 表，LEFT JOIN backtest_results 获取 annual_return
- [x] 1.3 在 FastAPI 应用中配置 CORSMiddleware，允许 localhost:5173 跨域访问（app/main.py）
- [x] 1.4 为新增的 2 个 API 编写单元测试（tests/unit/test_api_data.py、tests/unit/test_api_backtest_list.py）

## 2. 前端项目初始化

- [x] 2.1 使用 Vite 创建 React + TypeScript 项目到 web/ 目录，配置 pnpm
- [x] 2.2 安装核心依赖：antd、react-router-dom、axios、@tanstack/react-query、zustand、echarts、echarts-for-react
- [x] 2.3 配置 Vite proxy 将 /api 请求转发到 http://localhost:8000
- [x] 2.4 创建 Axios 实例（web/src/api/client.ts），配置 baseURL 和错误拦截器
- [x] 2.5 配置 React Query 的 QueryClientProvider（web/src/main.tsx）
- [x] 2.6 配置 React Router v6 路由表（web/src/router.tsx），包含 /、/workbench、/backtest、/backtest/new、/backtest/:taskId
- [x] 2.7 实现 AppLayout 组件（web/src/layouts/AppLayout.tsx），包含 Ant Design Sider 侧边导航

## 3. API 请求层

- [x] 3.1 实现策略 API 函数（web/src/api/strategy.ts）：fetchStrategyList、fetchStrategySchema、runStrategy
- [x] 3.2 实现回测 API 函数（web/src/api/backtest.ts）：runBacktest、fetchBacktestResult、fetchBacktestList
- [x] 3.3 实现数据 API 函数（web/src/api/data.ts）：fetchKline
- [x] 3.4 定义 TypeScript 类型（web/src/types/），与后端 Pydantic 模型对应

## 4. 选股工作台页面

- [x] 4.1 实现策略列表组件（web/src/pages/workbench/StrategyPanel.tsx），按分类分组展示策略，支持点击选择
- [x] 4.2 实现策略参数配置组件（web/src/pages/workbench/StrategyConfig.tsx），展示已选策略及其参数表单
- [x] 4.3 实现基础过滤配置组件（剔除 ST、剔除停牌复选框）
- [x] 4.4 实现选股结果表格组件（web/src/pages/workbench/ResultTable.tsx），展示代码、名称、现价、涨跌幅、匹配策略数、AI 评分、AI 信号，支持排序
- [x] 4.5 实现股票详情面板组件（web/src/pages/workbench/StockDetail.tsx），展示匹配策略列表和 AI 分析摘要
- [x] 4.6 组装选股工作台页面（web/src/pages/workbench/WorkbenchPage.tsx），集成策略配置 + 执行按钮 + 结果展示 + 详情面板

## 5. 回测中心页面

- [x] 5.1 实现回测任务列表页（web/src/pages/backtest/BacktestListPage.tsx），Ant Design Table 分页展示任务列表
- [x] 5.2 实现新建回测页面（web/src/pages/backtest/BacktestNewPage.tsx），包含策略选择、股票代码输入、日期范围、初始资金表单，提交后跳转到详情页
- [x] 5.3 实现绩效指标卡片组件（web/src/pages/backtest/MetricsCards.tsx），展示年化收益率、最大回撤、夏普比率、胜率、总交易次数、盈亏比
- [x] 5.4 实现收益曲线图组件（web/src/pages/backtest/EquityCurve.tsx），使用 ECharts 折线图展示净值曲线
- [x] 5.5 实现交易明细表组件（web/src/pages/backtest/TradesTable.tsx），展示买卖记录，买入红色卖出绿色
- [x] 5.6 组装回测结果详情页（web/src/pages/backtest/BacktestDetailPage.tsx），集成指标卡片 + 收益曲线 + 交易明细 + 轮询逻辑（React Query refetchInterval，3 秒，完成后停止）

## 6. 收尾

- [x] 6.1 更新 README.md，补充前端技术栈、启动方式、项目结构
- [x] 6.2 更新 CLAUDE.md，补充前端目录结构和依赖说明
- [x] 6.3 更新 .env.example，补充 CORS 相关配置项（如有）
