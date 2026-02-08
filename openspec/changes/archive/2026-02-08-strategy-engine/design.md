## Context

数据采集模块（BaoStock/AKShare → stock_daily）和技术指标计算引擎（→ technical_daily）已完成。现在需要构建策略引擎，将原始数据转化为选股结果。

设计文档 `02-详细设计-策略引擎.md` 定义了完整的 79 种策略和双模式接口，但 V1 范围（`99-实施范围` §三）明确要求大幅简化：扁平继承、单模式接口、手动注册、10-15 种核心策略、仅 AND 组合。

现有依赖：
- `DataManager.get_daily_bars()` — 查询日线数据
- `DataManager.get_latest_technical()` — 查询技术指标
- `DataManager.get_stock_list()` — 查询股票列表
- `technical_daily` 表 — 预计算的 23 个技术指标
- `finance_indicator` 表 — 财务指标
- `strategies` 表 — 策略配置（已建表）

## Goals / Non-Goals

**Goals:**
- 实现 BaseStrategy 抽象基类，统一 `filter_batch` 单模式接口
- 实现 10-15 种 V1 核心策略（技术面 + 基本面）
- 实现 StrategyFactory 手动注册机制
- 实现 Pipeline 5 层漏斗（Layer 1-4 完整实现，Layer 5 AI 留占位接口）
- 提供策略执行 HTTP API

**Non-Goals:**
- 不实现 `check_single` 双模式接口（V1 全部用 batch 模式）
- 不实现嵌套 OR 策略组合（V1 仅 AND）
- 不实现装饰器自动扫描注册（V1 手动字典）
- 不实现策略版本管理（V1 用 Git 管理）
- 不实现 Layer 5 AI 终审的实际调用（留接口占位）
- 不实现形态识别类策略（双底、头肩底等需要 single 模式）
- 不实现事件驱动、舆情、跟投类策略（V2 范围）

## Decisions

### Decision 1: 扁平继承 vs 多层抽象子类

**选择：扁平继承**

- 设计文档定义了 7 个中间抽象子类（TechnicalStrategy、FundamentalStrategy、PatternStrategy 等）
- V1 只有 10-15 种策略，中间层没有实际复用价值，徒增复杂度
- 所有策略直接继承 `BaseStrategy`，通过 `category` 属性区分类型
- V2 如果策略数量增长到 30+ 可以再引入中间层

### Decision 2: 统一 filter_batch 单模式 vs 双模式接口

**选择：统一 filter_batch 单模式**

- 设计文档定义了 `filter_batch`（批量向量化）和 `check_single`（逐只精细）双模式
- V1 不实现形态识别等需要逐只处理的策略，所有 V1 策略都可以向量化
- 统一接口签名：`filter_batch(df: DataFrame, target_date: date) -> Series[bool]`
- 输入 df 包含当日全市场数据（stock_daily + technical_daily JOIN），每行一只股票
- 简化 Pipeline 逻辑：不需要按模式分流

### Decision 3: V1 策略清单

基于设计文档 §3 和 §6.3，V1 选择以下 12 种策略：

**技术面（8 种）：**
1. `ma_cross` — 均线金叉（MA5 上穿 MA10，放量）
2. `macd_golden` — MACD 金叉（DIF 上穿 DEA）
3. `rsi_oversold` — RSI 超卖反弹（RSI6 < 20 后回升）
4. `kdj_golden` — KDJ 金叉（K 上穿 D，J < 20 区域）
5. `boll_breakthrough` — 布林带突破（价格突破下轨后回升）
6. `volume_breakout` — 放量突破（价格创 20 日新高 + 量比 > 2）
7. `ma_long_arrange` — 均线多头排列（MA5 > MA10 > MA20 > MA60）
8. `macd_divergence` — MACD 底背离（价格新低但 MACD 不创新低）

**基本面（4 种）：**
9. `low_pe_high_roe` — 低估值高成长（PE < 30, ROE > 15%）
10. `high_dividend` — 高股息（股息率 > 3%，PE < 20）
11. `growth_stock` — 成长股（营收增长 > 20%，利润增长 > 20%）
12. `financial_safety` — 财务安全（资产负债率 < 60%，流动比率 > 1.5）

### Decision 4: Pipeline 层级实现

V1 Pipeline 简化为 4 层（Layer 5 AI 留占位）：

```
Layer 1: SQL 粗筛 — 剔除 ST/退市/停牌/低流动性 → ~4000 只
Layer 2: 技术指标初筛 — 运行技术面策略（batch 向量化）→ ~500 只
Layer 3: 财务指标复筛 — 运行基本面策略（batch 向量化）→ ~100 只
Layer 4: 综合排序 — 按策略命中数 + 指标评分排序，取 Top N → ~30 只
Layer 5: AI 终审（占位）— 直接透传 Layer 4 结果
```

V1 简化点：
- Layer 2 和 Layer 3 合并执行逻辑（都是 filter_batch），仅通过策略 category 区分
- Layer 4 不做复杂评分，按命中策略数量降序排列
- Layer 5 直接返回 Layer 4 结果（AI 模块实现后再接入）

### Decision 5: 策略注册 — 手动字典 vs 装饰器

**选择：手动字典注册**

- 设计文档定义了 `@register_strategy` 装饰器 + `auto_discover_strategies()` 自动扫描
- V1 只有 12 种策略，手动注册更直观、更易调试
- 在 `factory.py` 中维护一个 `STRATEGY_REGISTRY` 字典
- V2 策略数量增长后可以切换到装饰器模式

### Decision 6: 策略执行结果存储

**选择：内存 + 数据库双存储**

- 策略执行是同步的（V1 不用 Redis 队列），结果直接返回
- 同时将执行结果写入 `strategies` 表的 `params` JSONB 字段记录最近一次执行
- API 返回结构包含：命中股票列表、每只股票的策略命中详情、执行耗时

### Decision 7: 目录结构

```
app/strategy/
├── __init__.py
├── base.py           # BaseStrategy 抽象基类
├── factory.py        # StrategyFactory + STRATEGY_REGISTRY
├── pipeline.py       # Pipeline 5 层漏斗
├── technical/        # 技术面策略
│   ├── __init__.py
│   ├── ma_cross.py
│   ├── macd_golden.py
│   ├── rsi_oversold.py
│   ├── kdj_golden.py
│   ├── boll_breakthrough.py
│   ├── volume_breakout.py
│   ├── ma_long_arrange.py
│   └── macd_divergence.py
└── fundamental/      # 基本面策略
    ├── __init__.py
    ├── low_pe_high_roe.py
    ├── high_dividend.py
    ├── growth_stock.py
    └── financial_safety.py
app/api/
└── strategy.py       # HTTP API 路由
```

## Risks / Trade-offs

- **[性能] 全市场 JOIN 数据量大** → Layer 1 SQL 粗筛先剔除 ~1000 只，Layer 2 只处理 ~4000 只股票的单日数据（一行一只），内存占用约 10MB，完全可控
- **[精度] 基本面策略依赖财务数据时效性** → 使用 `ann_date <= target_date` 过滤，确保不使用未来数据。财务数据可能滞后 1-2 个月，这是 A 股市场的固有限制
- **[扩展性] 手动注册不够灵活** → V1 只有 12 种策略，手动注册完全够用。V2 切换到装饰器模式时只需修改 factory.py，策略代码无需改动
- **[组合逻辑] 仅 AND 不够灵活** → V1 用户只能选择"同时满足所有策略"，无法表达"满足任一技术面策略 + 满足基本面策略"。V2 加入 OR 组合后解决
- **[AI 占位] Layer 5 无实际功能** → 接口已预留，AI 模块实现后可无缝接入，不影响 V1 选股功能完整性
