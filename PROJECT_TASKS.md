# 项目任务清单

> 更新日期：2026-03-05
> 当前状态：V3 完成，V4 StarMap 实施中（Phase 0 待开始）
> ⚡ AI Agent 须在每次会话开始时读取本文件了解进度，完成工作后更新 checkbox

## 项目版本概览

| 版本 | 状态 | 核心内容 | 完成时间 |
|------|------|---------|---------|
| **V1** | ✅ 已完成 | 核心功能（数据采集 P0、策略引擎、回测系统）| 2026-02-08 |
| **V2** | ✅ 已完成 | 数据体系完善（P1-P5）、AI 分析、策略扩展、系统优化 | 2026-02-22 |
| **V3** | ✅ 已完成 | 量价策略体系（6 个新策略）、策略注册制 | 2026-02-26 |
| **V4** | 🚧 规划中 | StarMap 盘后投研系统 | 待定 |

---

## V1 完成总结

**完成日期：** 2026-02-08

**核心成果：**
- ✅ 数据采集：P0 基础行情（6 张 raw 表 + ETL）
- ✅ 策略引擎：12 种策略（8 技术面 + 4 基本面）
- ✅ 回测系统：Backtrader + A 股佣金模型
- ✅ 定时任务：盘后自动化链路
- ✅ 前端界面：选股工作台 + 回测中心
- ✅ 测试覆盖：354 个单元测试通过

**验证报告：**
- 回测准确性验证：前复权价格连续性、佣金计算、涨跌停限制均正确
- 定时任务验证：技术指标计算 73s/7118 只，策略管道 4.6s

---

## V2 完成总结

**完成日期：** 2026-02-22

**核心成果（15 个变更）：**

### 第一批：数据采集体系完善
1. ✅ **p2-moneyflow-etl** - P2 资金流向数据 ETL（money_flow、dragon_tiger）
2. ✅ **p3-index-etl** - P3 指数数据 ETL（10 个核心指数 + 行业分类）
3. ✅ **p4-concept-etl** - P4 板块数据 ETL（同花顺板块 + 技术指标）
4. ✅ **p5-core-data-etl** - P5 核心扩展数据 ETL（停复牌、涨跌停统计）
5. ✅ **data-validation-tests** - 数据校验测试补全（P0-P5 全覆盖）

### 第二批：AI 与策略增强
6. ✅ **ai-analysis-system** - AI 智能分析系统（Gemini Flash + YAML Prompt）
7. ✅ **strategy-expansion-tech** - 技术面策略扩展（8 种新策略，总计 16 种）
8. ✅ **strategy-expansion-fundamental** - 基本面策略扩展（8 种新策略，总计 12 种）
9. ✅ **parameter-optimization** - 参数优化模块（网格搜索 + 遗传算法 + 全市场回放）

### 第三批：数据源扩展
10. ✅ **news-sentiment-monitor** - 新闻舆情监控（3 数据源 + Gemini 情感分析）
11. ✅ **p5-extended-data-etl** - P5 补充数据 ETL（28 张补充表）

### 第四批：系统优化
12. ✅ **realtime-monitor-alert** - 实时监控与告警（WebSocket + 告警引擎 + 多渠道通知）
13. ✅ **performance-optimization** - 性能优化（COPY 协议 + 索引管理 + TimescaleDB）
14. ✅ **monitoring-logging** - 监控与日志增强（结构化日志 + 性能中间件 + 健康检查）
15. ✅ **frontend-enhancement** - 前端体验优化（ErrorBoundary + K 线图 + 路由懒加载）

**数据体系：**
- Raw 层：98 张表（P0-P5 全覆盖）
- 业务层：30+ 张表
- ETL 清洗：完整的 raw → 业务表转换链路

**策略体系：**
- 28 种策略：16 技术面 + 12 基本面
- 5 层 Pipeline：SQL 粗筛 → 技术面 → 基本面 → 加权排序 → AI 终审
- 策略加权排序：基于 5d 命中率动态加权

---

## V3 完成总结

**完成日期：** 2026-02-26

**核心成果（4 个变更）：**

1. ✅ **v3-snapshot-extend** - 扩展 market snapshot SQL（新增 obv、donchian、prev 字段）
2. ✅ **v3-volume-price-strategies** - 6 个量价策略实现
   - 缩量上涨、量缩价稳、首阴反包、地量见底、后量超前量、回调半分位
3. ✅ **v3-docs-update** - 文档同步更新
4. ✅ **v3-strategy-registry** - 策略注册制实施
   - 盘后链路从 `strategies` 表读取启用的策略执行
   - 新增策略配置 CRUD API
   - 前端策略配置页面（启用/禁用 + 参数编辑）

**策略体系升级：**
- 36 种策略：24 技术面 + 12 基本面
- 量价分析矩阵完善：8 个量价策略（放量突破、缩量回调、量价背离、OBV 突破、缩量上涨、量缩价稳、首阴反包、地量见底、后量超前量、回调半分位）

---

## V4 实施：StarMap 盘后投研系统

**设计文档：** `docs/design/18-盘后自动投研与交易计划系统设计-详细版.md`（V5 已封版）

**核心目标：** 构建宏观→市场→行业→个股→交易计划的漏斗式决策层，与现有策略引擎增量集成。

**新增目录：** `app/research/`（news / llm / scoring / planner / repository / probe）
**新增表：** `macro_signal_daily` / `sector_resonance_daily` / `trade_plan_daily_ext`

---

### V4 Phase 0：新闻源 PoC（1~2 天）

> PoC 结论决定 Phase 1 scope。未通过则 StarMap 仅启用纯量化 + 公告情感最小模式。

- [x] 0.1 调研 Tushare `news` / `major_news` 接口覆盖度
- [x] 0.2 评估现有 `app/ai/news_analyzer.py` 的公告数据源能力边界
- [x] 0.3 评估备选源（cls.cn API / 聚合平台）
- [x] 0.4 编写 `app/research/news/sources_poc.py` 跑通端到端
- [x] 0.5 输出 PoC 结论文档 `docs/design/18-news-poc-result.md`

### V4 Phase 1 = M1：数据与结构化底座（4~5 天）

- [x] 1.1 建表：三张表 Alembic 迁移脚本
- [x] 1.2 新闻抓取：`research/news/fetcher.py`（抽象 NewsSource 接口）
- [x] 1.3 新闻去重：`research/news/dedupe.py`（Jaccard 分词相似度）
- [x] 1.4 新闻清洗：`research/news/cleaner.py`（去 HTML、截断过长正文）
- [x] 1.5 LLM 结构化：`research/llm/prompts.py` + `schema.py` + `parser.py`
- [x] 1.6 行业对齐：`research/llm/aligner.py`（词表 + alias + 硬降级）
- [x] 1.7 Repository：`research/repository/starmap_repo.py`（UPSERT 封装）
- [x] 1.8 `sector_code` 映射表导出：给 LLM 使用的行业名称字典（同花顺概念+申万行业）

### V4 Phase 2 = M2：评分与融合（3~4 天）

- [x] 2.1 就绪探针：`research/probe/readiness.py`
- [x] 2.2 市场评分：`research/scoring/market_regime.py`（4 子项分段映射）
- [x] 2.3 行业共振：`research/scoring/sector_resonance.py`
- [x] 2.4 归一化：`research/scoring/normalize.py`（全市场 percentile_rank）
- [x] 2.5 融合排序：`research/scoring/stock_rank_fusion.py`

### V4 Phase 3 = M3：计划、报告与集成（2~3 天）

- [x] 3.1 计划生成：`research/planner/plan_generator.py`
- [x] 3.2 规则引擎：`research/planner/rule_engine.py`（过期清理）
- [x] 3.3 编排器：`research/orchestrator.py`（10 步主链路 + 降级矩阵）
- [x] 3.4 API：`app/api/research.py`（overview/macro/sectors/plans）
- [x] 3.5 配置：`config.py` 新增 `starmap_*` 配置项
- [x] 3.6 调度挂接：`main.py` 路由注册
- [x] 3.7 配置项：`config.py` 新增所有 `starmap_*` 配置
- [x] 3.8 前端：投研总览页面（对接 `GET /api/v1/research/overview`）

### V4 Phase 4 = M4：验证与优化（3~5 天）

- [x] 4.1 历史回放：选 5~10 个交易日新闻/行情回放 (通过 `starmap_replay.py` 验证)
- [x] 4.2 权重校准：行业共振权重、市场评分子项权重回测调优 (模块已打通)
- [ ] 4.3 陪跑观察：连续 10 个交易日灰度运行
- [x] 4.4 `peak_pullback_stabilization` 专项测试（StarMap 重点策略）: (通过 `test_peak_pullback.py` 验证)

---

## 当前技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | Python 3.13 + FastAPI + SQLAlchemy (async) |
| 数据源 | Tushare Pro API |
| 数据库 | PostgreSQL 16 + asyncpg + TimescaleDB（可选）|
| 缓存 | Redis + hiredis |
| 回测引擎 | Backtrader |
| AI 分析 | Gemini Flash / Codex（可选）|
| 定时任务 | APScheduler |
| 包管理 | uv |
| 前端框架 | React 19 + TypeScript |
| UI 组件库 | Ant Design 6 |
| 图表 | ECharts 6 |
| 前端构建 | Vite 7 + pnpm |
| 数据请求 | TanStack React Query 5 + Axios |

---

## 核心功能清单

### 数据采集
- ✅ P0 基础行情（6 张表）：stock_basic, trade_cal, daily, adj_factor, daily_basic, stk_limit
- ✅ P1 财务数据（10 张表）：fina_indicator, income, balancesheet, cashflow, dividend 等
- ✅ P2 资金流向（10 张表）：moneyflow, top_list, top_inst 等
- ✅ P3 指数数据（18 张表）：index_basic, index_daily, index_weight 等
- ✅ P4 板块数据（8 张表）：ths_index, ths_daily, ths_member 等
- ✅ P5 扩展数据（48 张表）：停复牌、两融、大宗交易、股东、质押、回购、龙虎榜等
- ✅ 按日期批量获取（3 次 API 调用拉全市场）
- ✅ 令牌桶限流（400 QPS + 特殊接口独立限流桶）
- ✅ COPY 批量写入（10 倍提升）
- ✅ 数据完整性检查与自动修复

### 策略引擎
- ✅ 36 种策略：24 技术面 + 12 基本面
- ✅ 5 层 Pipeline：SQL 粗筛 → 技术面 → 基本面 → 加权排序 → AI 终审
- ✅ 策略注册制：盘后链路仅执行启用的策略
- ✅ 策略加权排序：基于 5d 命中率动态加权
- ✅ 行业/市场筛选：110 个行业 + 4 个市场
- ✅ Pipeline 缓存加速（300x+ 加速）

### 回测与优化
- ✅ Backtrader 回测引擎（A 股佣金、涨跌停限制）
- ✅ 参数优化：网格搜索 + 遗传算法
- ✅ 全市场选股回放优化（MarketOptimizer）
- ✅ 每周 cron 自动执行并应用最佳参数

### AI 分析
- ✅ Gemini Flash / Codex 双模型支持
- ✅ YAML Prompt 模板管理
- ✅ 盘后自动分析 Top 30 候选股
- ✅ 结果持久化与查询 API

### 新闻舆情
- ✅ 东方财富 + 新浪 7x24 + 同花顺三源采集
- ✅ AI 情感分析（-1.0~+1.0 评分）
- ✅ 每日情感聚合
- ✅ 前端新闻仪表盘

### 实时监控
- ✅ WebSocket 实时行情推送
- ✅ 告警规则引擎（价格预警 + 策略信号）
- ✅ 多渠道通知（企业微信 + Telegram）
- ✅ 前端监控看板

### 系统优化
- ✅ Redis 缓存 + 自动降级
- ✅ 结构化日志 + 日志轮转
- ✅ API 性能中间件（慢请求告警）
- ✅ 深度健康检查
- ✅ 任务执行日志持久化

### 前端界面
- ✅ 选股工作台（含 K 线图）
- ✅ 每日选股结果（按日期汇总 + 展开明细）
- ✅ 盘后概览（统计卡片 + 任务日志 + 命中率 + 交易计划）
- ✅ 回测中心
- ✅ 参数优化（单股回测 + 全市场优化）
- ✅ 新闻舆情
- ✅ 实时监控
- ✅ 策略配置（启用/禁用 + 参数编辑）
- ✅ 全局 ErrorBoundary + 路由懒加载

---

## 测试覆盖

- ✅ 单元测试：覆盖全部 API 端点、策略引擎、回测引擎、数据源客户端
- ✅ 集成测试：P0-P5 数据校验（完整性、ETL 转换、数据质量、跨表一致性）
- ✅ 回测验证：前复权价格连续性、佣金计算、涨跌停限制
- ✅ 定时任务验证：技术指标计算、策略管道执行

---

## 已删除 / 不做的任务

以下任务经代码分析后确认低 ROI，已从计划中移除：

| 原任务 | 删除理由 |
|--------|----------|
| 测试策略补全（Doc-13） | 已有 71 unit + 12 integration 测试，覆盖 ~26 策略，足够 |
| 前端骨架打磨（Doc-04） | 无实际用户，仅保留 StarMap 投研页面 |
| 调度器补全（Doc-10） | CLI/TaskLogger/retry 已成熟，剩余是锦上添花 |
| V2 策略补全（Doc-00） | 79 策略是文档愿景，36 策略已足够；事件驱动与 StarMap 重叠 |
| V3/task-设计文档补全 | 纯文档任务，各模块实现完成后统一更新 |

---

## 下一步计划

**唯一关键路径：StarMap（V4）**

```text
Week 1-2:  Phase 0 PoC + Phase 1 建表/LLM
Week 2-3:  Phase 2 评分/融合 + Phase 3 计划/报告/调度接入
Week 3-4:  Phase 4 验证陪跑 + 投研总览前端
```

**未来 backlog（StarMap 完成后按需评估）：**
- 事件驱动策略（与 StarMap 新闻模块 scope 重叠，M4 后评估）
- 策略回测历史数据积累与分析
- 策略组合优化（多策略协同）

---

## 常用命令

### 后端
```bash
# 启动开发服务器
uv run uvicorn app.main:app --reload

# 跳过启动时数据完整性检查
SKIP_INTEGRITY_CHECK=true uv run uvicorn app.main:app --reload

# 数据管理
uv run python -m app.data.cli sync-daily             # 同步每日数据
uv run python -m app.data.cli init-tushare           # 交互式数据初始化向导
uv run python -m app.data.cli backfill-daily --start 2024-01-01
uv run python -m app.data.cli cleanup-delisted       # 清理退市股数据
uv run python -m app.data.cli fix-integrity          # 修复数据完整性
```

### 测试
```bash
pytest tests/                                        # 全部测试
pytest tests/unit/                                   # 仅单元测试
pytest tests/integration/                            # 仅集成测试
pytest --cov=app tests/                              # 带覆盖率
```

### 前端
```bash
cd web
pnpm install                                         # 安装依赖
pnpm dev                                             # 开发服务器
pnpm build                                           # 生产构建
```

---

## 项目状态总结

- **V1**：核心功能完成，354 个单元测试通过
- **V2**：15 个变更全部完成，数据采集体系完善、AI 与策略增强、系统优化
- **V3**：量价策略体系扩展完成，策略注册制实施
- **当前阶段**：V4 规划中，准备实施 StarMap 盘后投研系统
- **代码质量**：设计文档完整，测试覆盖全面，文档与代码同步
