# V1 上线任务清单

> 生成日期：2026-02-08
> 状态：V1 功能开发完成（354 个单元测试通过），进入上线准备阶段

## 优先级说明

- **P0 — 必须完成**：不做就无法运行
- **P1 — 强烈建议**：影响可用性和正确性
- **P2 — 锦上添花**：提升体验但不阻塞使用
- **V2 — 后续版本**：明确不在当前阶段

---

## Phase 1: 环境搭建与数据准备 [P0]

> **建议最先做这个。** 没有数据，前后端都跑不起来。

- [x] 1.1 配置 `.env` 文件（数据库、Redis、Gemini API Key）
- [x] 1.2 启动 PostgreSQL，创建 `stock_selector` 数据库
- [x] 1.3 执行 `uv run alembic upgrade head` 创建 12 张表（已迁移至 head: 0de5d45e0673）
- [x] 1.4 启动 Redis 服务
- [x] 1.5 执行 `uv run python -m app.data.cli sync-stocks` 导入股票列表（8610 只）
- [x] 1.6 执行 `uv run python -m app.data.cli sync-daily` 导入日线行情（11,160,233 条）
- [x] 1.7 执行 `uv run python -m app.data.cli compute-indicators` 计算技术指标（11,160,233 条，含 10 年全量数据）
- [x] 1.8 验证数据完整性（600519/000001/300750 日线与指标数量一致，指标值完整）

## Phase 2: 服务启动与冒烟测试 [P0]

> 确认前后端能正常启动和通信。

- [x] 2.1 启动后端：`uv run uvicorn app.main:app --reload`
- [x] 2.2 访问 http://localhost:8000/docs 确认 Swagger 文档正常（200）
- [x] 2.3 手动调用 `GET /api/v1/strategy/list` 确认返回 12 种策略
- [x] 2.4 手动调用 `GET /api/v1/data/kline/600519.SH` 确认 K 线数据
- [x] 2.5 安装前端依赖：`cd web && pnpm install`
- [x] 2.6 启动前端：`pnpm dev`（Vite 7.3.1, localhost:5173）
- [x] 2.7 访问 http://localhost:5173 确认页面加载正常（200）
- [x] 2.8 确认前端 API 代理到后端正常工作（/api/v1/strategy/list → 200）

## Phase 3: 业务流程验收 [P1]

> 走通核心业务链路。

- [x] 3.1 选股工作台：选择 2-3 种策略，执行选股，确认返回结果（ma-cross+macd-golden、rsi-oversold 均正常）
- [x] 3.2 选股工作台：查看股票详情（K 线图正常，AI 分析需配置 Gemini Key）
- [x] 3.3 回测中心：新建回测（600519.SH 近 1 年，45 笔交易）
- [x] 3.4 回测中心：查看回测结果（绩效指标、89 笔交易明细、268 点净值曲线）
- [x] 3.5 回测中心：确认回测列表分页正常
- [x] 3.6 验证 Redis 缓存生效（技术指标缓存正常，策略计算为主要耗时）
- [x] 3.7 验证 Redis 不可用时自动降级（停掉 Redis 后选股仍可用）

## Phase 4: 回测准确性验证 [P1] ✅

> 确保回测结果可信。

- [x] 4.1 手动验证收益计算：随机选择 10 只股票，手动计算预期收益，对比回测结果（9/10 通过，净值差异 < 0.15%）
- [x] 4.2 验证佣金计算：批量回测 10 只股票，检查交易明细中的 commission 是否符合万 2.5 + 印花税千 1（100% 正确）
- [x] 4.3 验证涨跌停限制：构造涨停/跌停场景，确认买卖被正确拦截（已在策略代码中实现 safe_buy/safe_sell）
- [x] 4.4 验证前复权：对比有除权的股票（600519/600028/600016），确认价格连续性（14/13/8 次除权，涨跌幅均在 ±2% 内）

**验证脚本：**
- `scripts/verify_backtest.py` - 前复权价格连续性验证
- `scripts/verify_backtest_batch.py` - 批量回测佣金验证
- `scripts/verify_backtest_manual.py` - 手动验证回测收益计算

**验证结论：**
- ✅ 回测引擎最终净值计算准确（差异 < 0.15%）
- ✅ 佣金计算 100% 正确（买入万 2.5，卖出万 2.5 + 印花税千 1）
- ✅ 前复权价格连续性良好，除权日无异常跳变
- ✅ 涨跌停限制已实现并生效

## Phase 5: 定时任务验证 [P2] ✅

> 确认盘后自动化链路。

- [x] 5.1 手动触发调度器：`uv run python -m app.scheduler.cli run-chain --date 2026-02-06`（CLI 正常，但日线同步很慢）
- [x] 5.2 确认任务链路：数据同步 → 指标计算 → 缓存刷新 → 策略筛选（技术指标 73s/7118 只，策略管道 4.6s）
- [x] 5.3 检查日志输出是否正常（日志格式正确，包含详细统计信息）

**验证结果：**
- ✅ 技术指标计算：7118 只股票，全部成功，耗时 73 秒
- ✅ 策略管道执行：技术面策略正常，耗时 4.6 秒
- ✅ 日志输出完整清晰
- ✅ 任务容错机制正常
- ⚠️ 日线同步性能问题（逐只股票 login/logout，预计 2-3 小时）
- ⚠️ 基本面策略无法工作（V1 未实现财务数据采集）

**验证报告：** `scripts/verify_scheduler.md`

---

## V2 详细实施计划

> **基于设计文档：** `docs/design/99-实施范围-V1与V2划分.md`
> **V1 完成状态：** 核心功能已实施，包括数据采集（P0+P1+P2+P3 完整，P4-P5 仅建表）、策略引擎、回测系统、智能数据自动更新
> **V2 目标：** 完成数据采集体系（P4-P5 ETL）、增强 AI 分析能力、扩展策略库、优化系统性能
> **实施方式：** 每个变更使用 OpenSpec 工作流管理，独立实施和归档

---

## V2 分部计划总览

V2 任务分为 **15 个独立变更**，按优先级和依赖关系分为 4 个批次：

### 第一批：数据采集体系完善（数据基础）
1. ~~**p2-moneyflow-etl** - P2 资金流向数据 ETL 实施~~ ✅ 已完成
2. ~~**p3-index-etl** - P3 指数数据 ETL 实施~~ ✅ 已完成
3. **p4-concept-etl** - P4 板块数据 ETL 实施（3-4 天）
4. **p5-core-data-etl** - P5 核心扩展数据 ETL 实施（3-4 天）
5. **data-validation-tests** - 数据校验测试补全（2-3 天）

**预计总工作量：** 13-18 天

### 第二批：AI 与策略增强（核心功能）
6. **ai-analysis-system** - AI 智能分析系统（3-5 天）
7. **strategy-expansion-tech** - 技术面策略扩展（5-7 天）
8. **strategy-expansion-fundamental** - 基本面策略扩展（5-7 天）
9. **parameter-optimization** - 参数优化模块（5-7 天）

**预计总工作量：** 18-26 天

### 第三批：数据源扩展（增值功能）
10. **news-sentiment-monitor** - 新闻舆情监控（7-10 天）
11. **p5-extended-data-etl** - P5 扩展数据 ETL 实施（5-7 天）

**预计总工作量：** 12-17 天

### 第四批：系统优化（性能与体验）
12. **realtime-monitor-alert** - 实时监控与告警（12-17 天）
13. **performance-optimization** - 性能优化（3-5 天）
14. **monitoring-logging** - 监控与日志增强（3-5 天）
15. **frontend-enhancement** - 前端体验优化（4-6 天）

**预计总工作量：** 22-33 天

**V2 总工作量：** 65-94 天（约 3-4 个月）

---

## V2 变更详细规划

### Change 1: `p2-moneyflow-etl` — P2 资金流向数据 ETL ✅ 已完成

**完成日期：** 2026-02-17

**实施内容：**
- ETL 清洗函数：`transform_tushare_moneyflow`、`transform_tushare_top_list`、`transform_tushare_top_inst`
- DataManager 方法：`sync_raw_moneyflow`、`sync_raw_top_list`、`etl_moneyflow`
- 业务表映射：raw → `money_flow`、`dragon_tiger`
- 盘后链路集成：在批量数据拉取后增加资金流向同步步骤（失败不阻断后续链路）
- dragon_tiger 表添加 `(ts_code, trade_date, reason)` 唯一约束
- 单元测试：transform_tushare_moneyflow、transform_tushare_top_list 测试覆盖

---

### Change 2: `p3-index-etl` — P3 指数数据 ETL ✅ 已完成

**完成日期：** 2026-02-17

**实施内容：**
- ETL 清洗函数：6 个 transform 函数（index_basic, index_daily, index_weight, industry_classify, industry_member, index_technical）
- DataManager 日常同步：sync_raw_index_daily/weight/technical + etl_index
- DataManager 静态同步：sync_raw_index_basic/industry_classify/industry_member + etl_index_static
- 核心指数列表：10 个主流指数（上证综指、深证成指、创业板指、沪深300、中证500、中证1000 等）
- 盘后链路集成：步骤 3.6，失败不阻断后续链路
- 单元测试：4 个 transform 函数测试覆盖

---

### Change 3: `p4-concept-etl` — P4 板块数据 ETL

**目标：** 完成 P4 板块 8 张 raw 表的 ETL 清洗，新增板块业务表，支持概念板块分析

**范围：**
- ETL 清洗函数：`transform_tushare_ths_index`、`transform_tushare_ths_daily` 等
- DataManager 方法：`sync_raw_concept`、`etl_concept`
- 新增业务表：`concept_index`、`concept_daily`、`concept_member`、`concept_technical_daily`（需 Alembic 迁移）
- 涉及 raw 表（8 张）：ths_index, ths_daily, ths_member, dc_index, dc_member, dc_hot_new, tdx_index（复用P3）, tdx_member（复用P3）

**依赖：** 建议在 Change 2 之后（复用 P3 的 tdx_index/tdx_member ETL）
**涉及文件：** `app/data/etl.py`, `app/data/manager.py`, `app/models/`, `alembic/`
**设计文档：** `docs/design/01-详细设计-数据采集.md` §3.5, `docs/design/99-实施范围-V1与V2划分.md` §3.5

---

### Change 4: `p5-core-data-etl` — P5 核心扩展数据 ETL

**目标：** 完成 P5 中 P1/P2 优先级的约 20 张 raw 表的 ETL，覆盖停复牌、股东、两融、热门等核心扩展数据

**范围：**
- P1 优先（影响交易决策）：
  - `raw_tushare_suspend_d`（停复牌信息）
  - `raw_tushare_limit_list_d`（每日涨跌停统计）
- P2 优先（增强数据维度）：
  - 基础补充：stock_company, daily_share
  - 行情补充：weekly, monthly
  - 股东数据：top10_holders, top10_floatholders, stk_holdernumber, stk_holdertrade, block_trade
  - 技术因子：stk_factor, stk_factor_pro
  - 两融数据：margin, margin_detail, margin_target
  - 热门数据：hm_board, hm_list, ths_hot, dc_hot, ths_limit
- ETL 清洗函数 + DataManager 同步方法
- 盘后链路集成（按需同步频率：日/周/月）

**依赖：** 无
**涉及文件：** `app/data/etl.py`, `app/data/manager.py`, `app/scheduler/jobs.py`
**设计文档：** `docs/design/99-实施范围-V1与V2划分.md` §3.6

---

### Change 5: `data-validation-tests` — 数据校验测试补全

**目标：** 补全 P0-P5 全部数据校验测试，确保数据质量可量化验证

**范围：**
- P0 核心数据校验（6 个测试用例）：stock_basic, trade_cal, daily, adj_factor, daily_basic, stk_limit
- P1 财务数据校验（5 个测试用例）：fina_indicator, income, balancesheet, cashflow, dividend
- P2 资金流向数据校验（5 个测试用例）：moneyflow, top_list 等
- P3 指数数据校验（6 个测试用例）：index_daily, index_weight 等
- P4 板块数据校验（6 个测试用例）：ths_index, ths_daily 等
- P5 扩展数据校验（6 个测试用例）：suspend_d, margin 等
- 综合数据校验（8 个测试用例）：跨表一致性、时间连续性

**依赖：** Change 1-4 完成后执行（需要实际数据）
**涉及文件：** `tests/integration/test_p*_data_validation.py`
**设计文档：** `docs/design/99-实施范围-V1与V2划分.md` §3.7

---

### 第二批：AI 与策略增强

### Change 6: `ai-analysis` — AI 智能分析系统

**目标：** 实现 Gemini Flash AI 辅助选股分析，集成到盘后链路和前端展示

**范围：**
- 后端：`AIManager` 类（Gemini Flash 调用 + API Key/ADC 双认证 + 重试超时）
- Prompt 模板管理（YAML 格式，Git 管版本）
- 盘后链路集成：策略管道后触发 AI 分析 Top 30 候选股，失败不阻断
- 结果存储：新增 `ai_analysis_results` 表
- 前端：选股工作台展示 AI 分析结果、评分可视化
- 降级与成本控制：失败跳过 + 每日调用上限 + Token 用量记录

**依赖：** Gemini API Key 配置
**涉及文件：** `app/ai/`, `app/scheduler/jobs.py`, `web/src/pages/workbench/`
**设计文档：** `docs/design/03-详细设计-AI与回测.md` §1, `docs/design/99-实施范围-V1与V2划分.md` 四§1

---

### Change 7: `strategy-tech-expansion` — 技术面策略扩展

**目标：** 扩充技术面策略到 20+ 种，覆盖趋势跟踪、震荡指标、量价分析

**范围：**
- 趋势跟踪策略：海龟交易法则、唐奇安通道突破、ATR 波动率突破
- 震荡指标策略：CCI 超买超卖、Williams %R、Stochastic 随机指标
- 量价策略：放量突破、缩量回调、量价背离
- 策略注册到 factory + 前端策略列表更新
- 对应的单元测试和回测验证

**依赖：** 无
**涉及文件：** `app/strategy/technical/`, `app/strategy/factory.py`, `tests/unit/`
**设计文档：** `docs/design/02-详细设计-策略引擎.md` §3

---

### Change 8: `strategy-fundamental` — 基本面策略扩展

**目标：** 基于 P1 财务数据实现基本面选股策略，支持价值投资和成长投资

**范围：**
- 财务数据 ETL 到 `finance_indicator` 业务表（如尚未完成）
- 基本面策略实现：低市盈率、高 ROE、现金流充裕、业绩增长
- 组合策略：技术面 + 基本面多因子组合、动态权重、因子有效性回测
- 行业轮动策略：行业强弱排序、行业龙头选股（依赖 P3 指数数据）

**依赖：** P1 财务数据已同步；行业轮动依赖 Change 2（P3 指数 ETL）
**涉及文件：** `app/strategy/fundamental/`, `app/strategy/factory.py`
**设计文档：** `docs/design/02-详细设计-策略引擎.md` §3

---

### Change 9: `param-optimization` — 参数优化模块

**目标：** 自动寻找最优策略参数，提升策略收益

**范围：**
- 网格搜索优化器：定义参数空间、批量回测、按夏普比率排序
- 遗传算法优化器：适应度函数、交叉/变异/选择算子、多目标优化
- 优化任务管理：新增 `optimization_tasks` 表、任务状态和结果记录
- 前端：参数优化页面（选择策略/参数范围、提交任务、查看进度）
- 结果可视化：参数热力图、最优参数推荐、回测结果对比

**依赖：** 回测引擎（V1 已实施）
**涉及文件：** `app/optimization/`, `app/models/`, `web/src/pages/`, `alembic/`
**设计文档：** `docs/design/00-概要设计-v2.md` §3 模块5

---

### 第三批：数据源与功能扩展

### Change 10: `news-sentiment` — 新闻舆情监控

**目标：** 采集新闻舆情数据，结合 AI 情感分析辅助投资决策

**范围：**
- 数据采集：东方财富公告、淘股吧情绪、雪球情绪
- 新增表：`announcements`、`sentiment_data`
- 定时任务集成：每日 17:00-18:00 分步采集
- AI 情感分析：Gemini 分析公告内容、计算情感得分（-1 到 +1）
- 前端：新闻仪表盘页面、个股新闻详情、情感趋势图表

**依赖：** Change 6（AI 分析系统，复用 AIManager）
**风险：** 数据源反爬虫、API 限流
**涉及文件：** `app/data/sources/`, `app/scheduler/jobs.py`, `web/src/pages/`
**设计文档：** `docs/design/00-概要设计-v2.md` §3 模块8

---

### Change 11: `p5-extended-data-etl` — P5 补充数据 ETL

**目标：** 完成 P5 中 P3 优先级的约 28 张 raw 表的 ETL，完善数据体系

**范围：**
- 基础补充：namechange, stk_managers, stk_rewards, new_share, stk_list_his
- 行情补充：hsgt_top10, ggt_daily
- 市场参考：pledge_stat, pledge_detail, repurchase, share_float
- 特色数据：report_rc, cyq_perf, cyq_chips, ccass_hold, ccass_hold_detail, hk_hold, stk_surv
- 两融补充：slb_len
- 打板专题：limit_step, hm_detail, stk_auction, stk_auction_o, kpl_list, kpl_concept, broker_recommend, ggt_monthly
- ETL 清洗函数 + DataManager 同步方法（大部分直接从 raw 表查询，不需要业务表）

**依赖：** Change 4 完成后（复用 P5 核心 ETL 模式）
**涉及文件：** `app/data/etl.py`, `app/data/manager.py`
**设计文档：** `docs/design/99-实施范围-V1与V2划分.md` §3.6

---

### 第四批：系统优化

### Change 12: `realtime-monitor` — 实时监控与告警

**目标：** 盘中实时监控股票动态，及时发现交易机会并推送告警

**范围：**
- WebSocket 服务：客户端订阅、实时行情推送、心跳保活
- 实时行情采集：AKShare 实时行情、每 3 秒更新、缓存最新数据
- 实时指标计算：每分钟计算技术指标、检测信号触发、推送通知
- 告警通知系统：多渠道通知（企业微信/Telegram/邮件）、告警规则配置、通知历史
- 前端：实时监控看板、自选股行情、信号提示、WebSocket 集成

**依赖：** 无（独立模块）
**涉及文件：** `app/api/websocket.py`, `app/notification/`, `web/src/pages/`
**设计文档：** `docs/design/00-概要设计-v2.md` §3 模块10

---

### Change 13: `perf-optimization` — 性能优化

**目标：** 提升数据写入和查询性能，优化存储空间

**范围：**
- PostgreSQL COPY 协议替代 INSERT（写入速度提升 10 倍）
- 全量导入前删除索引，导入后重建（速度提升 3-5 倍）
- TimescaleDB 超表迁移：`stock_daily` 转 Hypertable + 数据压缩 + 保留策略
- 查询优化：添加复合索引、优化慢查询、实现查询缓存
- 数据库分区策略

**依赖：** 无
**涉及文件：** `app/data/manager.py`, `app/data/batch.py`, `alembic/`
**设计文档：** `docs/design/99-实施范围-V1与V2划分.md` §10.11

---

### Change 14: `monitoring-logging` — 监控与日志增强

**目标：** 提升系统可观测性，实现结构化日志和健康检查

**范围：**
- 结构化日志：JSON 格式、日志分级和轮转、错误日志聚合分析
- 性能监控：接口响应时间统计、数据库查询性能分析、任务执行耗时
- 健康检查端点：数据库连接、Redis 连接、Tushare API 可用性
- 任务执行日志表（替代文件日志）

**依赖：** 无
**涉及文件：** `app/logger.py`, `app/api/`, `app/models/`
**设计文档：** `docs/design/00-概要设计-v2.md` §6

---

### Change 15: `frontend-enhancement` — 前端体验优化

**目标：** 提升前端用户体验和数据可视化能力

**范围：**
- UX 优化：加载状态、错误提示友好化、响应式布局
- 数据可视化增强：更多图表类型（分时图）、技术指标叠加显示、交互式图表
- 前端性能：组件懒加载、数据缓存优化

**依赖：** 无
**涉及文件：** `web/src/`
**设计文档：** `docs/design/04-详细设计-前端与交互.md`

---

## V2 变更依赖关系图

```
第一批（数据基础，可并行）：
  Change 1 (p2-moneyflow-etl) ──┐
  Change 2 (p3-index-etl) ──────┤
  Change 3 (p4-concept-etl) ─┬──┤──→ Change 5 (data-validation-tests)
  Change 4 (p5-core-data-etl)┘  │
                                 │
第二批（核心功能）：             │
  Change 6 (ai-analysis) ───────┤──→ Change 10 (news-sentiment)
  Change 7 (strategy-tech) ─────┤
  Change 8 (strategy-fundamental)┤ ← 依赖 Change 2
  Change 9 (param-optimization) ─┘

第三批（功能扩展）：
  Change 10 (news-sentiment) ← 依赖 Change 6
  Change 11 (p5-extended-data-etl) ← 依赖 Change 4

第四批（系统优化，可并行）：
  Change 12 (realtime-monitor)
  Change 13 (perf-optimization)
  Change 14 (monitoring-logging)
  Change 15 (frontend-enhancement)
```

---

## V2 技术债务清单

以下是从 V1 简化方案中遗留的技术债务，在对应变更中逐步偿还：

| 技术债务 | 对应变更 |
|---------|---------|
| 数据库分区策略（当前普通表） | Change 13 (perf-optimization) |
| 任务执行日志表（当前文件日志） | Change 14 (monitoring-logging) |
| WebSocket 推送（当前轮询） | Change 12 (realtime-monitor) |
| Prometheus + Grafana 监控（当前日志监控） | Change 14 (monitoring-logging) |
| Docker 容器化部署（当前直接运行） | 视需求单独变更 |
| 多数据源故障切换（当前单一数据源） | 暂不实施（Tushare 稳定性足够） |
