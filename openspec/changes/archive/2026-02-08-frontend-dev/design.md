## Context

后端已完成全部 7 个核心模块，提供了以下 API：

- `POST /api/v1/strategy/run` — 执行选股
- `GET /api/v1/strategy/list` — 策略列表
- `GET /api/v1/strategy/schema/{name}` — 策略参数
- `POST /api/v1/backtest/run` — 执行回测
- `GET /api/v1/backtest/result/{task_id}` — 回测结果

前端项目 `web/` 目前为空，需要从零搭建。系统为单机单人使用，无需考虑多用户、权限、SSR 等复杂场景。

## Goals / Non-Goals

**Goals:**

- 搭建可维护的前端项目结构，开发体验流畅（HMR、类型检查）
- 实现选股工作台：策略选择 → 参数配置 → 执行 → 结果展示
- 实现回测中心：提交回测 → 查看结果（绩效指标 + 收益曲线 + 交易明细）
- 补充后端缺失的 2 个 API（K 线查询、回测列表）
- 后端配置 CORS 支持前端开发服务器

**Non-Goals:**

- 不做用户认证/权限系统
- 不做 WebSocket 实时推送（V1 用轮询）
- 不做实时监控看板、新闻舆情页面
- 不做 SSR/SSG，纯 SPA 即可
- 不做移动端适配
- 不做国际化

## Decisions

### D1: 构建工具 — Vite

**选择**: Vite 6
**理由**: 开发启动快（ESM 原生）、HMR 即时、配置简单。CRA 已不再推荐，Next.js 对纯 SPA 过重。
**替代方案**: Create React App（已弃用）、Next.js（SSR 不需要）

### D2: 状态管理 — Zustand

**选择**: Zustand
**理由**: 轻量（< 1KB）、API 简洁、无 Provider 嵌套。项目状态简单（策略配置、选股结果、回测状态），不需要 Redux 的复杂度。
**替代方案**: Redux Toolkit（过重）、Jotai（原子化对本项目无优势）

### D3: 数据请求 — TanStack Query + Axios

**选择**: @tanstack/react-query + axios
**理由**: React Query 提供缓存、自动重试、轮询（refetchInterval）、loading/error 状态管理。Axios 提供拦截器统一处理错误和 baseURL。
**替代方案**: SWR（功能略少）、原生 fetch（需手写缓存和重试）

### D4: 图表库 — ECharts

**选择**: echarts + echarts-for-react
**理由**: 设计文档指定。K 线图（candlestick）和收益曲线（line）支持完善，中文文档丰富。
**替代方案**: Recharts（无 K 线图）、AntV G2（学习成本高）

### D5: 包管理器 — pnpm

**选择**: pnpm
**理由**: 磁盘效率高（硬链接）、安装速度快、严格的依赖隔离。
**替代方案**: npm（慢）、yarn（无明显优势）

### D6: 前后端通信 — CORS + 代理

**选择**: 开发环境用 Vite proxy 转发 `/api` 到后端 `localhost:8000`，生产环境后端直接 serve 前端静态文件。
**理由**: 开发时避免 CORS 问题，生产部署简单（单进程）。后端仍需配置 CORS 作为备选。

### D7: 轮询策略

**选择**: React Query 的 `refetchInterval` 实现轮询
- 回测任务状态：每 3 秒轮询，任务完成后自动停止
- 不需要选股轮询（选股 API 是同步返回的）
**理由**: React Query 原生支持条件轮询（`refetchInterval` 可以是函数），无需手写 setInterval。

### D8: 路由结构

```
/                    → 重定向到 /workbench
/workbench           → 智能选股工作台
/backtest            → 回测任务列表
/backtest/new        → 新建回测
/backtest/:taskId    → 回测结果详情
```

**选择**: React Router v6，扁平路由，AppLayout 包裹侧边导航。

### D9: 后端补充 API 设计

**K 线查询**: `GET /api/v1/data/kline/{ts_code}?start_date=&end_date=&limit=120`
- 从 `stock_daily` 表查询，返回 OHLCV 数据
- 默认返回最近 120 个交易日

**回测列表**: `GET /api/v1/backtest/list?page=1&page_size=20`
- 从 `backtest_tasks` 表分页查询，按创建时间倒序
- 返回任务基本信息（id、策略名、状态、创建时间、绩效摘要）

## Risks / Trade-offs

**[ECharts 包体积大]** → 使用按需引入（只导入 candlestick、line、bar 组件），配合 Vite tree-shaking 减小体积。

**[Ant Design 5 样式体积]** → 使用 CSS-in-JS（antd v5 默认），无需额外 CSS 导入，支持 tree-shaking。

**[轮询效率]** → V1 单人使用，轮询频率低（3 秒），对后端压力可忽略。V2 可升级为 WebSocket。

**[前端无测试]** → V1 优先交付功能，前端暂不写单元测试。后端 API 已有测试覆盖。
