# 项目任务清单

> 更新日期：2026-03-04
> 当前状态：V3 完成，进入 V4 规划阶段

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

## V4 规划：StarMap 盘后投研系统

**设计文档：** `docs/design/18-盘后自动投研与交易计划系统设计-详细版.md`

**核心目标：**
- 宏观事件层：新闻 + LLM 结构化（风险偏好、利好/利空行业）
- 市场状态层：宽基指数 + 情绪指标 + 风险评分
- 行业共振层：消息面 + 资金面 + 价格面融合评分
- 个股执行层：策略结果二次编排 + 量纲统一
- 计划交付层：交易计划（Entry/Stop/TP/Position）+ 报告推送

**新增表：**
- `macro_signal_daily`：宏观结构化信号
- `sector_resonance_daily`：行业共振评分
- `trade_plan_daily_ext`：交易计划扩展

**实施方式：** OpenSpec 工作流，分阶段实施

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

## 设计文档归档

**活跃文档（`docs/design/`）：**
- `00-概要设计-v2.md` - 65% 完成
- `04-详细设计-前端与交互.md` - 70% 完成
- `10-系统设计-定时任务调度.md` - 75% 完成
- `13-系统设计-测试策略.md` - 60% 完成
- `18-盘后自动投研与交易计划系统设计-详细版.md` - 未开始
- `99-实施范围-V1与V2划分.md` - 持续更新
- `99-项目总体计划.md` - 持续更新
- `00-V3概要设计.md` - 部分完成
- `01-V3实施计划.md` - 部分完成

**已归档文档（`docs/design/archived/`）：**
- `01-详细设计-数据采集.md` - 100% 完成
- `02-详细设计-策略引擎.md` - 100% 完成
- `03-详细设计-AI与回测.md` - 100% 完成
- `05-详细设计-量价综合选股策略.md` - 100% 完成
- `11-系统设计-缓存策略.md` - 100% 完成
- `12-系统设计-Pipeline缓存优化.md` - 100% 完成
- `14-系统设计-V4量价配合策略优化任务.md` - 100% 完成
- `15-策略设计-高位回落企稳二次启动.md` - 100% 完成
- `v4_planning/01-V4详细设计-量价配合策略.md` - 100% 完成

---

## 下一步计划

### 短期（V4 Phase 1）
- [ ] StarMap 宏观事件层实施
- [ ] StarMap 市场状态层实施
- [ ] StarMap 行业共振层实施

### 中期（V4 Phase 2）
- [ ] StarMap 个股执行层实施
- [ ] StarMap 计划交付层实施
- [ ] 前端 StarMap 仪表盘

### 长期优化
- [ ] 策略回测历史数据积累与分析
- [ ] 策略组合优化（多策略协同）
- [ ] 风控模块增强（仓位管理、止损止盈）

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
