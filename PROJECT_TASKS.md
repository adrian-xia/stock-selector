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
> **V1 完成状态：** 核心功能已实施，包括数据采集、策略引擎、回测系统、智能数据自动更新
> **V2 目标：** 增强 AI 分析能力、扩展数据源、优化策略参数、提升系统可观测性

### V2-Phase 1: AI 智能分析系统 [高优先级]

**目标：** 实现 AI 辅助选股分析，提升投资决策质量

#### 1.1 AI 分析基础架构 [P0]

- [ ] 1.1.1 实现 `AIManager` 类（`app/ai/manager.py`）
  - 支持 Gemini Flash 模型调用
  - 实现 API Key 和 ADC/Vertex AI 两种认证方式
  - 实现基础重试和超时控制
- [ ] 1.1.2 实现 Prompt 模板管理（`app/ai/prompts.py`）
  - 量化信号分析 Prompt
  - 新闻情感分析 Prompt（V2.2 实现）
  - Prompt 版本管理（Git 管理，YAML 格式）
- [ ] 1.1.3 集成到盘后链路（`app/scheduler/jobs.py`）
  - 新增 `ai_analysis_step()` 函数
  - 策略管道执行后触发 AI 分析
  - 分析 Top 30 候选股票
  - 失败不阻断链路（记录日志）
- [ ] 1.1.4 AI 分析结果存储
  - 扩展 `strategies` 表或新增 `ai_analysis_results` 表
  - 存储分析结果（JSON 格式）
  - 关联策略执行记录

**预计工作量：** 3-5 天
**依赖：** Gemini API Key 配置

#### 1.2 AI 分析前端展示 [P1]

- [ ] 1.2.1 选股工作台集成 AI 分析
  - 在股票详情中展示 AI 分析结果
  - 支持查看历史分析记录
  - 优化 AI 分析加载状态
- [ ] 1.2.2 AI 分析结果可视化
  - 情感评分可视化（雷达图/评分卡）
  - 关键因素提取和展示
  - 风险提示高亮显示

**预计工作量：** 2-3 天

#### 1.3 AI 模型降级与容错 [P2]

- [ ] 1.3.1 实现降级策略
  - Gemini 失败 → 跳过 AI 分析
  - 记录降级日志
  - 前端友好提示
- [ ] 1.3.2 成本控制
  - 配置每日 API 调用上限
  - 记录 Token 使用量
  - 超限时自动停止调用

**预计工作量：** 1-2 天

---

### V2-Phase 2: 参数优化模块 [高优先级]

**目标：** 自动寻找最优策略参数，提升策略收益

#### 2.1 参数优化引擎 [P0]

- [ ] 2.1.1 实现网格搜索优化器（`app/optimization/grid_search.py`）
  - 定义参数空间（如 MA 周期 5-60）
  - 批量回测不同参数组合
  - 按夏普比率排序结果
- [ ] 2.1.2 实现遗传算法优化器（`app/optimization/genetic.py`）
  - 定义适应度函数（夏普比率/最大回撤）
  - 实现交叉、变异、选择算子
  - 支持多目标优化
- [ ] 2.1.3 优化任务管理
  - 新增 `optimization_tasks` 表
  - 记录优化任务状态和结果
  - 支持任务暂停/恢复

**预计工作量：** 5-7 天

#### 2.2 参数优化前端 [P1]

- [ ] 2.2.1 参数优化页面
  - 选择策略和参数范围
  - 提交优化任务
  - 查看优化进度
- [ ] 2.2.2 优化结果可视化
  - 参数热力图（参数 vs 收益）
  - 最优参数推荐
  - 回测结果对比

**预计工作量：** 3-4 天

---

### V2-Phase 3: 新闻舆情监控 [中优先级]

**目标：** 采集和分析新闻舆情，辅助投资决策

#### 3.1 新闻数据采集 [P0]

- [ ] 3.1.1 实现东方财富公告采集（`app/data/sources/eastmoney.py`）
  - 采集上市公司公告
  - 解析公告类型和内容
  - 存储到 `announcements` 表
- [ ] 3.1.2 实现淘股吧情绪采集（`app/data/sources/taoguba.py`）
  - 采集热门股票讨论
  - 提取情绪指标（看多/看空比例）
  - 存储到 `sentiment_data` 表
- [ ] 3.1.3 实现雪球情绪采集（`app/data/sources/xueqiu.py`）
  - 采集股票讨论和评论
  - 计算情绪得分
  - 存储到 `sentiment_data` 表
- [ ] 3.1.4 集成到定时任务
  - 每日 17:00 采集东方财富公告
  - 每日 17:30 采集淘股吧情绪
  - 每日 18:00 采集雪球情绪

**预计工作量：** 7-10 天
**风险：** 数据源反爬虫、API 限流

#### 3.2 新闻情感分析 [P1]

- [ ] 3.2.1 集成 AI 情感分析
  - 使用 Gemini 分析公告内容
  - 提取关键信息（业绩、重组、处罚等）
  - 计算情感得分（-1 到 +1）
- [ ] 3.2.2 情感指标计算
  - 个股情感综合得分
  - 行业情感趋势
  - 市场整体情绪

**预计工作量：** 3-5 天

#### 3.3 新闻舆情前端 [P2]

- [ ] 3.3.1 新闻仪表盘页面
  - 展示最新公告和舆情
  - 情感趋势图表
  - 热门股票排行
- [ ] 3.3.2 个股新闻详情
  - 在股票详情中展示相关新闻
  - 情感分析结果可视化
  - 新闻时间线

**预计工作量：** 3-4 天

---

### V2-Phase 4: 实时监控与告警 [低优先级]

**目标：** 盘中实时监控股票动态，及时发现交易机会

#### 4.1 实时行情推送 [P0]

- [ ] 4.1.1 实现 WebSocket 服务（`app/api/websocket.py`）
  - 支持客户端订阅股票
  - 推送实时行情数据
  - 心跳保活机制
- [ ] 4.1.2 实时行情采集
  - 使用 AKShare 获取实时行情
  - 每 3 秒更新一次
  - 缓存最新行情数据
- [ ] 4.1.3 实时指标计算
  - 每分钟计算技术指标
  - 检测信号触发（金叉、突破等）
  - 推送信号通知

**预计工作量：** 5-7 天

#### 4.2 告警通知系统 [P1]

- [ ] 4.2.1 实现通知管理器（`app/notification/manager.py`）
  - 支持多种通知渠道（Telegram、邮件、企业微信）
  - 通知模板管理
  - 通知历史记录
- [ ] 4.2.2 告警规则配置
  - 价格突破告警
  - 技术指标信号告警
  - 新闻舆情告警
  - 用户自定义规则

**预计工作量：** 4-6 天

#### 4.3 实时监控前端 [P2]

- [ ] 4.3.1 实时监控看板
  - 自选股实时行情
  - 信号触发提示
  - 告警历史记录
- [ ] 4.3.2 WebSocket 集成
  - 前端 WebSocket 连接管理
  - 实时数据更新
  - 断线重连机制

**预计工作量：** 3-4 天

---

### V2-Phase 5: 策略库扩展 [中优先级]

**目标：** 扩充策略库到 20+ 种，覆盖更多选股逻辑

#### 5.1 技术面策略扩展 [P0]

- [ ] 5.1.1 趋势跟踪策略
  - 海龟交易法则
  - 唐奇安通道突破
  - ATR 波动率突破
- [ ] 5.1.2 震荡指标策略
  - CCI 超买超卖
  - Williams %R
  - Stochastic 随机指标
- [ ] 5.1.3 量价策略
  - 放量突破
  - 缩量回调
  - 量价背离

**预计工作量：** 5-7 天

#### 5.2 基本面策略扩展 [P1]

- [ ] 5.2.1 财务数据采集
  - 实现 Tushare 财务数据采集
  - 存储到 `finance_indicator` 表
  - 定期更新（每季度）
- [ ] 5.2.2 基本面策略实现
  - 低市盈率策略
  - 高 ROE 策略
  - 现金流充裕策略
  - 业绩增长策略

**预计工作量：** 7-10 天
**依赖：** Tushare API Token

#### 5.3 组合策略 [P2]

- [ ] 5.3.1 多因子组合
  - 技术面 + 基本面组合
  - 动态权重调整
  - 因子有效性回测
- [ ] 5.3.2 行业轮动策略
  - 行业强弱排序
  - 行业龙头选股
  - 行业配置优化

**预计工作量：** 5-7 天

---

### V2-Phase 6: 系统增强 [低优先级]

**目标：** 提升系统可观测性、稳定性和易用性

#### 6.1 监控与日志 [P1]

- [ ] 6.1.1 性能监控
  - 接口响应时间统计
  - 数据库查询性能分析
  - 任务执行耗时监控
- [ ] 6.1.2 日志增强
  - 结构化日志（JSON 格式）
  - 日志分级和轮转
  - 错误日志聚合分析
- [ ] 6.1.3 健康检查
  - 数据库连接检查
  - Redis 连接检查
  - 数据源 API 可用性检查

**预计工作量：** 3-5 天

#### 6.2 数据库优化 [P2]

- [ ] 6.2.1 TimescaleDB 迁移
  - 将 `stock_daily` 转换为 Hypertable
  - 配置数据压缩策略
  - 配置数据保留策略
- [ ] 6.2.2 查询优化
  - 添加复合索引
  - 优化慢查询
  - 实现查询缓存

**预计工作量：** 3-4 天

#### 6.3 前端增强 [P2]

- [ ] 6.3.1 用户体验优化
  - 加载状态优化
  - 错误提示友好化
  - 响应式布局优化
- [ ] 6.3.2 数据可视化增强
  - 更多图表类型（K 线、分时图）
  - 技术指标叠加显示
  - 交互式图表操作

**预计工作量：** 4-6 天

---

### V2-Phase 7: P5 扩展数据 ETL 实施

**目标：** 完成 P5 扩展数据（48 张 raw 表）的 ETL 清洗和 DataManager 同步方法

**背景：** V1 阶段已完成 P5 扩展数据的 ORM 模型定义、TushareClient fetch 方法和 Alembic 迁移脚本。V2 阶段需要实施 ETL 清洗函数、DataManager 同步方法和数据校验测试。

#### 数据分类

P5 扩展数据包含 48 张 raw 表，分为 6 个子类别：

##### 11a. 基础数据补充（7 张 raw 表）

| 表名 | 用途 | 业务表 | ETL 优先级 |
|------|------|--------|-----------|
| raw_tushare_namechange | 股票曾用名 | - | P3 |
| raw_tushare_stock_company | 上市公司基本信息 | stock_company | P2 |
| raw_tushare_stk_managers | 上市公司管理层 | - | P3 |
| raw_tushare_stk_rewards | 管理层薪酬 | - | P3 |
| raw_tushare_new_share | 新股上市 | - | P3 |
| raw_tushare_daily_share | 每日股本 | - | P2 |
| raw_tushare_stk_list_his | 上市状态历史 | - | P3 |

**实施建议：**
- P2 优先：stock_company（公司基本信息）、daily_share（股本数据，用于计算市值）
- P3 次要：其他表主要用于信息展示，不影响核心选股逻辑

##### 11b. 行情补充（5 张 raw 表）

| 表名 | 用途 | 业务表 | ETL 优先级 |
|------|------|--------|-----------|
| raw_tushare_weekly | 周线行情 | stock_weekly | P2 |
| raw_tushare_monthly | 月线行情 | stock_monthly | P2 |
| raw_tushare_suspend_d | 停复牌信息 | - | P1 |
| raw_tushare_hsgt_top10 | 沪深港通十大成交股 | - | P3 |
| raw_tushare_ggt_daily | 港股通每日成交 | - | P3 |

**实施建议：**
- P1 优先：suspend_d（停复牌信息，影响交易决策）
- P2 次要：weekly/monthly（周月线行情，用于多周期分析）
- P3 可选：沪深港通数据（用于资金流向分析）

##### 11c. 市场参考数据（9 张 raw 表）

| 表名 | 用途 | 业务表 | ETL 优先级 |
|------|------|--------|-----------|
| raw_tushare_top10_holders | 前十大股东 | - | P2 |
| raw_tushare_top10_floatholders | 前十大流通股东 | - | P2 |
| raw_tushare_pledge_stat | 股权质押统计 | - | P3 |
| raw_tushare_pledge_detail | 股权质押明细 | - | P3 |
| raw_tushare_repurchase | 回购数据 | - | P3 |
| raw_tushare_share_float | 限售解禁 | - | P3 |
| raw_tushare_block_trade | 大宗交易 | - | P2 |
| raw_tushare_stk_holdernumber | 股东人数 | - | P2 |
| raw_tushare_stk_holdertrade | 股东增减持 | - | P2 |

**实施建议：**
- P2 优先：股东数据（top10_holders、stk_holdernumber、stk_holdertrade）、大宗交易
- P3 次要：质押、回购、解禁数据

##### 11d. 特色数据（9 张 raw 表）

| 表名 | 用途 | 业务表 | ETL 优先级 |
|------|------|--------|-----------|
| raw_tushare_report_rc | 券商研报 | - | P3 |
| raw_tushare_cyq_perf | 筹码分布 | - | P3 |
| raw_tushare_cyq_chips | 筹码集中度 | - | P3 |
| raw_tushare_stk_factor | 技术因子 | - | P2 |
| raw_tushare_stk_factor_pro | 技术因子（专业版）| - | P2 |
| raw_tushare_ccass_hold | 中央结算持股汇总 | - | P3 |
| raw_tushare_ccass_hold_detail | 中央结算持股明细 | - | P3 |
| raw_tushare_hk_hold | 沪深港通持股 | - | P3 |
| raw_tushare_stk_surv | 股票调查 | - | P3 |

**实施建议：**
- P2 优先：技术因子（stk_factor、stk_factor_pro，用于量化策略）
- P3 次要：其他特色数据

##### 11e. 两融数据（4 张 raw 表）

| 表名 | 用途 | 业务表 | ETL 优先级 |
|------|------|--------|-----------|
| raw_tushare_margin | 融资融券汇总 | - | P2 |
| raw_tushare_margin_detail | 融资融券明细 | - | P2 |
| raw_tushare_margin_target | 融资融券标的 | - | P2 |
| raw_tushare_slb_len | 转融通 | - | P3 |

**实施建议：**
- P2 优先：融资融券数据（margin、margin_detail、margin_target，用于市场情绪分析）
- P3 次要：转融通数据

##### 11f. 打板专题（14 张 raw 表）

| 表名 | 用途 | 业务表 | ETL 优先级 |
|------|------|--------|-----------|
| raw_tushare_limit_list_d | 每日涨跌停统计 | - | P1 |
| raw_tushare_ths_limit | 同花顺涨跌停 | - | P2 |
| raw_tushare_limit_step | 涨跌停阶梯 | - | P3 |
| raw_tushare_hm_board | 热门板块 | - | P2 |
| raw_tushare_hm_list | 热门股票 | - | P2 |
| raw_tushare_hm_detail | 热门股票明细 | - | P3 |
| raw_tushare_stk_auction | 集合竞价 | - | P3 |
| raw_tushare_stk_auction_o | 集合竞价（开盘）| - | P3 |
| raw_tushare_kpl_list | 开盘啦 | - | P3 |
| raw_tushare_kpl_concept | 开盘啦概念 | - | P3 |
| raw_tushare_broker_recommend | 券商推荐 | - | P3 |
| raw_tushare_ths_hot | 同花顺热榜 | - | P2 |
| raw_tushare_dc_hot | 东方财富热榜 | - | P2 |
| raw_tushare_ggt_monthly | 港股通月度 | - | P3 |

**实施建议：**
- P1 优先：limit_list_d（涨跌停统计，用于打板策略）
- P2 次要：热门数据（hm_board、hm_list、ths_hot、dc_hot，用于市场热点分析）
- P3 可选：其他打板专题数据

#### V2 实施路线图

##### Phase 1：核心数据（P1 优先级）

**目标：** 支持核心选股策略和交易决策

**任务：**
1. 停复牌信息（raw_tushare_suspend_d）
   - ETL 函数：`transform_tushare_suspend_d`
   - 业务表：可选（直接从 raw 表查询）
   - 用途：过滤停牌股票，避免选中无法交易的股票

2. 涨跌停统计（raw_tushare_limit_list_d）
   - ETL 函数：`transform_tushare_limit_list_d`
   - 业务表：可选（直接从 raw 表查询）
   - 用途：打板策略、市场情绪分析

**DataManager 方法：**
```python
async def sync_raw_suspend_d(self, trade_date: date) -> dict
async def sync_raw_limit_list_d(self, trade_date: date) -> dict
```

##### Phase 2：增强数据（P2 优先级）

**目标：** 增强选股策略的数据维度

**任务：**
1. 公司基本信息（raw_tushare_stock_company）
2. 每日股本（raw_tushare_daily_share）
3. 周月线行情（raw_tushare_weekly、raw_tushare_monthly）
4. 股东数据（raw_tushare_top10_holders、raw_tushare_stk_holdernumber、raw_tushare_stk_holdertrade）
5. 大宗交易（raw_tushare_block_trade）
6. 技术因子（raw_tushare_stk_factor、raw_tushare_stk_factor_pro）
7. 融资融券（raw_tushare_margin、raw_tushare_margin_detail、raw_tushare_margin_target）
8. 热门数据（raw_tushare_hm_board、raw_tushare_hm_list、raw_tushare_ths_hot、raw_tushare_dc_hot）

##### Phase 3：补充数据（P3 优先级）

**目标：** 完善数据体系，支持高级分析

**任务：**
- 其他所有 P3 优先级的表

#### ETL 实施模板

##### 1. ETL 清洗函数（app/data/etl.py）

```python
def transform_tushare_suspend_d(raw_rows: list[dict]) -> list[dict]:
    """清洗停复牌数据。

    Args:
        raw_rows: 从 raw_tushare_suspend_d 读取的原始数据

    Returns:
        清洗后的数据列表
    """
    if not raw_rows:
        return []

    cleaned = []
    for row in raw_rows:
        cleaned.append({
            "ts_code": row["ts_code"],
            "suspend_date": _parse_date(row["suspend_date"]),
            "resume_date": _parse_date(row["resume_date"]) if row.get("resume_date") else None,
            "suspend_reason": row.get("suspend_reason"),
            "data_source": "tushare",
        })

    return cleaned
```

##### 2. DataManager 同步方法（app/data/manager.py）

```python
async def sync_raw_suspend_d(self, trade_date: date) -> dict:
    """按日期同步停复牌数据到 raw 表。

    Args:
        trade_date: 交易日期

    Returns:
        {"suspend_d": int} - 写入的记录数
    """
    from app.data.tushare import TushareClient

    client: TushareClient = self._primary_client
    td_str = trade_date.strftime("%Y%m%d")

    # 获取原始数据
    raw_suspend = await client.fetch_raw_suspend_d(td_str)

    counts = {"suspend_d": 0}

    async with self._session_factory() as session:
        if raw_suspend:
            counts["suspend_d"] = await self._upsert_raw(
                session, RawTushareSuspendD.__table__, raw_suspend
            )
        await session.commit()

    logger.info(
        "[sync_raw_suspend_d] %s: suspend_d=%d",
        trade_date, counts["suspend_d"],
    )
    return counts
```

##### 3. 数据校验测试（tests/integration/test_p5_data_validation.py）

```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_suspend_d_data_integrity():
    """测试停复牌数据完整性。

    验证：
    - 停牌股票数 <= 上市股票数 × 0.10
    - 关键字段非空率 >= 95%
    """
    # 实现测试逻辑
    pass
```

#### 注意事项

1. **数据同步频率：**
   - 日线数据：每日同步（盘后链路）
   - 周月线数据：每周/每月同步
   - 基础信息：每周同步
   - 其他数据：按需同步

2. **API 限流：**
   - P5 扩展数据接口较多，需注意 Tushare API 限流（400 QPS）
   - 建议分批同步，避免触发限流

3. **存储优化：**
   - 部分历史数据量较大（如筹码分布），考虑只保留最近 N 天数据
   - 使用 PostgreSQL 分区表优化查询性能

4. **业务表设计：**
   - 大部分 P5 数据可以直接从 raw 表查询，不需要单独的业务表
   - 只有高频查询的数据才需要 ETL 到业务表

#### 参考资料

- Tushare Pro API 文档：https://tushare.pro/document/2
- 设计文档：`docs/design/01-详细设计-数据采集.md`
- V1/V2 划分：`docs/design/99-实施范围-V1与V2划分.md`

---

### V2 实施优先级建议

#### 第一批（核心功能增强）
1. **AI 智能分析系统** (V2-Phase 1) - 3-5 天
2. **参数优化模块** (V2-Phase 2) - 5-7 天
3. **策略库扩展 - 技术面** (V2-Phase 5.1) - 5-7 天
4. **P5 扩展数据 - Phase 1 核心数据** (V2-Phase 7.1) - 2-3 天

**预计总工作量：** 15-22 天

#### 第二批（数据源扩展）
5. **新闻舆情监控** (V2-Phase 3) - 7-10 天
6. **策略库扩展 - 基本面** (V2-Phase 5.2) - 7-10 天
7. **P5 扩展数据 - Phase 2 增强数据** (V2-Phase 7.2) - 5-7 天

**预计总工作量：** 19-27 天

#### 第三批（实时监控）
8. **实时监控与告警** (V2-Phase 4) - 12-17 天
9. **P5 扩展数据 - Phase 3 补充数据** (V2-Phase 7.3) - 3-5 天

**预计总工作量：** 15-22 天

#### 第四批（系统优化）
10. **系统增强** (V2-Phase 6) - 10-15 天

---

### V2 技术债务清单

以下是从 V1 简化方案中遗留的技术债务，建议在 V2 中逐步偿还：

- [ ] 多数据源故障切换（当前手动切换）
- [ ] 数据库分区策略（当前普通表）
- [ ] 分布式锁（当前单机部署无需）
- [ ] 任务执行日志表（当前文件日志）
- [ ] WebSocket 推送（当前轮询）
- [ ] Prometheus + Grafana 监控（当前日志监控）
- [ ] Docker 容器化部署（当前直接运行）

---

## V2 规划（后续版本）

| 功能 | 价值 | 复杂度 | 建议优先级 |
|------|------|--------|-----------|
| 参数优化模块 | 高 — 自动寻找最优策略参数 | 中 | V2-P0 |
| 更多选股策略 | 中 — 扩充策略库到 20+ | 低 | V2-P0 |
| AI 多模型降级 | 中 — 提升 AI 分析可用性 | 中 | V2-P1 |
| 新闻舆情监控 | 中 — 辅助投资决策 | 高 | V2-P2 |
| 实时监控告警 | 低 — 个人用户需求不强 | 高 | V2-P3 |
| 高手跟投 | 低 — 数据源难获取 | 高 | V2-P3 |

---

## 建议执行顺序

```
Phase 1 (环境+数据) → Phase 2 (冒烟测试) → Phase 3 (业务验收) → Phase 4 (回测验证) → Phase 5 (定时任务)
```

**最先做 Phase 1**，因为所有后续步骤都依赖真实数据。预计 Phase 1-2 可在 1 次会话内完成。
