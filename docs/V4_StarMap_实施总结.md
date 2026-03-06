# V4 StarMap 盘后投研系统 - 实施总结

**部署日期：** 2026-03-06
**当前状态：** 陪跑观察期（预计持续至 2026-03-20）
**项目版本：** V4
**设计文档：** `docs/design/18-盘后自动投研与交易计划系统设计-详细版.md`（V5 已封版）

---

## 一、项目概述

StarMap 是一个盘后自动投研系统，构建了宏观→市场→行业→个股→交易计划的漏斗式决策层，与现有策略引擎增量集成。

**核心目标：**
- 自动化投研流程：从宏观信号到交易计划的全链路自动化
- 多维度评分融合：市场状态、行业共振、个股策略三层评分
- 智能降级机制：数据缺失时自动降级，保证系统可用性
- 前端可视化：投研总览页面，直观展示分析结果

---

## 二、实施进度

### Phase 0：新闻源 PoC（已完成）
- ✅ 调研 Tushare news 接口覆盖度
- ✅ 评估现有公告数据源能力边界
- ✅ 评估备选源（cls.cn API / 聚合平台）
- ✅ 端到端 PoC 验证
- ✅ 输出 PoC 结论文档

### Phase 1：数据与结构化底座（已完成）
- ✅ 三张表 Alembic 迁移（macro_signal_daily / sector_resonance_daily / trade_plan_daily_ext）
- ✅ 新闻抓取、去重、清洗模块
- ✅ LLM 结构化（prompts / schema / parser）
- ✅ 行业对齐与 Repository 封装
- ✅ sector_code 映射表导出

### Phase 2：评分与融合（已完成）
- ✅ 就绪探针（readiness.py）
- ✅ 市场评分（market_regime.py，4 子项分段映射）
- ✅ 行业共振（sector_resonance.py）
- ✅ 归一化（normalize.py，全市场 percentile_rank）
- ✅ 融合排序（stock_rank_fusion.py）

### Phase 3：计划、报告与集成（已完成）
- ✅ 计划生成（plan_generator.py）
- ✅ 规则引擎（rule_engine.py，过期清理）
- ✅ 编排器（orchestrator.py，10 步主链路 + 降级矩阵）
- ✅ API（app/api/research.py，overview/macro/sectors/plans）
- ✅ 配置（config.py 新增 starmap_* 配置项）
- ✅ 调度挂接（main.py 路由注册）
- ✅ 前端（投研总览页面）

### Phase 4：验证与优化（进行中）
- ✅ 历史回放（starmap_replay.py 验证 5 个交易日）
- ✅ 权重校准（模块已打通）
- 🚧 陪跑观察（已部署 Docker，定时任务 16:10 执行，需持续观察半个月至 2026-03-20）
- ✅ peak_pullback_stabilization 专项测试
- ✅ 全面测试（34 个单元测试通过，API 端点验证）

---

## 三、核心功能

### 1. 数据库表结构

**macro_signal_daily（宏观信号日表）**
- trade_date（唯一）、risk_appetite、global_risk_score
- positive_sectors、negative_sectors、macro_summary
- key_drivers、raw_payload、content_hash

**sector_resonance_daily（行业共振日表）**
- trade_date + sector_code（唯一约束）
- news_score、moneyflow_score、trend_score、final_score
- confidence、drivers

**trade_plan_daily_ext（交易计划扩展表）**
- trade_date + ts_code + source_strategy（唯一约束）
- plan_type、plan_status、entry_rule、stop_loss_rule
- position_suggestion、market_regime、confidence
- reasoning、risk_flags

### 2. 核心模块

**新闻处理（app/research/news/）**
- fetcher.py：抽象 NewsSource 接口
- dedupe.py：Jaccard 分词相似度去重
- cleaner.py：去 HTML、截断过长正文

**LLM 结构化（app/research/llm/）**
- prompts.py：Prompt 模板管理
- schema.py：Pydantic 数据模型
- parser.py：LLM 输出解析
- aligner.py：行业名称对齐

**评分引擎（app/research/scoring/）**
- market_regime.py：市场状态评分
- sector_resonance.py：行业共振评分
- normalize.py：全市场归一化
- stock_rank_fusion.py：个股融合排序

**计划生成（app/research/planner/）**
- plan_generator.py：交易计划生成
- rule_engine.py：规则引擎

**编排器（app/research/orchestrator.py）**
- 10 步主链路：过期清理 → 就绪探针 → 新闻管道 → 市场评分 → 行业共振 → 个股排序 → 计划生成 → 持久化 → 缓存刷新 → 汇总
- 降级矩阵：INDEX_DATA_MISSING / NO_NEWS_DATA / MACRO_SIGNAL_FAILED / SECTOR_RESONANCE_FAILED

### 3. API 端点

**路由前缀：** `/research`

- GET /research/overview：投研总览
- GET /research/macro：宏观信号详情
- GET /research/sectors：行业共振列表
- GET /research/plans：交易计划列表

### 4. 前端页面

**路径：** web/src/pages/research/ResearchPage.tsx

**功能：**
- 日期选择器
- 宏观概览卡片（风险偏好、全球风险评分、热门行业数、交易计划数）
- 宏观摘要（利好/利空行业标签）
- Tabs 切换（行业共振表 + 交易计划表）

---

## 四、测试覆盖

### 单元测试（34 个，全部通过）

**文件：** tests/test_starmap_core.py

- dedupe 模块（7 个测试）
- cleaner 模块（4 个测试）
- aligner 模块（5 个测试）
- parser 模块（6 个测试）
- normalize 模块（6 个测试）
- schema 模块（3 个测试）
- prompts 模块（3 个测试）

### 集成测试

- 历史回放验证：scripts/starmap_replay.py 验证 5 个交易日
- API 端点验证：overview / macro / sectors / plans 全部返回正常
- 降级机制验证：INDEX_DATA_MISSING / NO_NEWS_DATA 降级正常工作

---

## 五、部署状态

### Docker 部署

**容器名称：** stock-selector
**状态：** Running

**服务组件：**
- nginx：前端静态文件服务（端口 5173）
- uvicorn：后端 API 服务（端口 8000）
- supervisor：进程管理

**数据库连接：**
- PostgreSQL：192.168.1.100:5432
- Redis：192.168.1.100:6379

**定时任务：**
- StarMap 投研：每个交易日 16:10 执行
- 盘后链路：每个交易日 16:00 执行

### 访问地址

- 前端：http://localhost:5173
- 后端：http://localhost:8000
- 健康检查：http://localhost:8000/health
- API 文档：http://localhost:8000/docs

---

## 六、已知问题

### 1. 时区显示问题

**位置：** web/src/pages/post-market/PostMarketPage.tsx 第 54 行

**现象：** 盘后概览页面显示任务执行时间为早上 8:00，实际应为下午 16:00（北京时间）

**原因：** 后端存储 UTC 时间（08:00 UTC = 16:00 北京时间），前端直接显示未转换

**解决方案：** 添加 dayjs 时区转换

### 2. API 路由不一致

**现象：** research router 使用 `/research` 前缀，其他 router 使用 `/api/v1/xxx`

**影响：** 路由风格不统一，但不影响功能

**解决方案：** 统一修改为 `/api/v1/research`（低优先级）

### 3. 数据降级

**现象：** 部分交易日缺失宏观信号和行业共振数据

**原因：** 新闻数据源未配置或 LLM 调用失败

**影响：** 系统自动降级，仍能生成交易计划（基于策略引擎）

**状态：** 符合设计预期，降级机制正常工作

---

## 七、技术亮点

### 1. 智能降级机制
系统在数据缺失时自动降级，保证核心功能可用

### 2. 多维度评分融合
三层评分体系：市场层、行业层、个股层

### 3. 全市场归一化
使用 percentile_rank 归一化，消除不同评分维度的量纲差异

### 4. UPSERT 幂等写入
所有数据写入使用 UPSERT，支持重复执行

### 5. 异步并发
使用 asyncio 并发执行独立任务，提升性能

---

## 八、总结

V4 StarMap 盘后投研系统已完成开发和部署，进入陪跑观察期。

**关键成果：**
- ✅ 完整的投研链路：宏观→市场→行业→个股→交易计划
- ✅ 智能降级机制：数据缺失时自动降级
- ✅ 多维度评分融合：市场、行业、个股三层评分
- ✅ 前端可视化：投研总览页面
- ✅ 定时任务集成：每日 16:10 自动执行
- ✅ Docker 部署：容器化部署

**测试覆盖：**
- 34 个单元测试全部通过
- 历史回放验证 5 个交易日
- API 端点全部验证通过
- 降级机制验证通过

**部署状态：**
- Docker 容器运行正常
- 所有服务健康
- 定时任务已配置
- 数据库连接正常

**下一步：**
- 陪跑观察期：2026-03-06 ~ 2026-03-20（约半个月）
- 观察指标：宏观信号质量、行业共振准确性、交易计划效果、降级频率、系统稳定性
- 观察期结束后根据数据反馈进行优化调整
