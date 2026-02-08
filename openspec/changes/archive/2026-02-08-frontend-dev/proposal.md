## Why

后端 7 个核心模块（数据采集、技术指标、策略引擎、回测引擎、定时任务、Redis 缓存、AI 分析）已全部完成，但系统缺少用户界面，无法实际使用。需要构建前端应用，让用户能够配置策略、执行选股、提交回测并查看结果。

## What Changes

- 新建 `web/` 前端项目（React 18 + TypeScript + Ant Design 5 + ECharts）
- 实现智能选股工作台页面：策略配置面板 + 筛选结果表格 + 股票详情
- 实现回测中心：回测任务列表、新建回测向导、回测结果详情（绩效指标 + 收益曲线 + 交易明细）
- 补充后端缺失的 API：K 线数据查询、回测任务列表
- 使用轮询替代 WebSocket 获取异步任务状态

## Capabilities

### New Capabilities

- `web-project-scaffold`: 前端项目初始化（Vite + React 18 + TS + Ant Design 5 + 路由 + Axios + React Query）
- `workbench-page`: 智能选股工作台页面（策略列表加载、策略参数配置、执行选股、结果表格、AI 分析展示）
- `backtest-pages`: 回测中心页面（任务列表、新建回测向导、结果详情页含收益曲线和交易明细）
- `kline-api`: 后端 K 线数据查询接口（`GET /api/v1/data/kline/{ts_code}`，供前端图表使用）
- `backtest-list-api`: 后端回测任务列表接口（`GET /api/v1/backtest/list`，供回测中心列表页使用）

### Modified Capabilities

（无需修改现有 spec 的行为要求）

## Impact

- **新增目录**：`web/` 前端项目（React + TypeScript）
- **后端新增**：`app/api/data.py` K 线查询路由、`app/api/backtest.py` 补充列表接口
- **依赖新增**：前端 npm 依赖（react、antd、echarts、axios、@tanstack/react-query、zustand、react-router-dom）
- **配置变更**：后端需配置 CORS 允许前端开发服务器访问
- **文档更新**：README.md、CLAUDE.md 需补充前端相关说明
