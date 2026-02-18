## Context

当前系统有 8 种技术面策略（均线金叉、MACD 金叉、RSI 超卖反弹、KDJ 金叉、布林带突破、放量突破、均线多头排列、MACD 底背离），覆盖了均线交叉和经典震荡指标的基础信号。`technical_daily` 表已有 23 个指标字段（MA/MACD/KDJ/RSI/BOLL/VOL/ATR），指标计算引擎 `app/data/indicator.py` 支持泛化计算和增量更新。

新增 8 种策略需要 4 个新指标（WR、CCI、BIAS、OBV），这些指标在现有计算框架中不存在，需要扩展 `compute_indicators_generic` 函数和 `technical_daily` 表。

所有策略遵循扁平继承 `BaseStrategy`，实现 `filter_batch` 返回布尔 Series 的统一模式。

## Goals / Non-Goals

**Goals:**
- 新增 8 种技术面策略，使技术面策略总数达到 16 种
- 新增 WR、CCI、BIAS、OBV 四个技术指标的计算和持久化
- 保持现有架构不变（扁平继承、手动注册、batch 模式）
- 所有新策略配套单元测试

**Non-Goals:**
- 不新增中间抽象子类或改变继承结构
- 不引入策略版本管理或参数优化
- 不修改 Pipeline 执行逻辑
- 不新增外部依赖

## Decisions

### D1: 新增指标字段方案 — Alembic migration 扩展 technical_daily

在 `technical_daily` 表新增 4 个 nullable 字段：`wr`（Numeric(10,4)）、`cci`（Numeric(10,4)）、`bias`（Numeric(10,4)）、`obv`（Numeric(20,2)）。

**理由**：与现有 23 个指标字段保持一致的存储模式，Pipeline 查询时一次 JOIN 即可获取所有指标。OBV 使用 Numeric(20,2) 是因为 OBV 是累积成交量，数值范围远大于其他指标。

**备选方案**：新建独立指标表 → 增加 JOIN 复杂度，不值得。

### D2: 指标计算公式

| 指标 | 公式 | 参数 |
|------|------|------|
| WR(14) | `(HH14 - close) / (HH14 - LL14) * -100` | 周期 14 |
| CCI(14) | `(TP - SMA(TP,14)) / (0.015 * MAD(TP,14))`，TP = (H+L+C)/3 | 周期 14 |
| BIAS(20) | `(close - MA20) / MA20 * 100` | 基于 MA20 |
| OBV | `cumsum(sign(close_change) * vol)`，平盘时 vol=0 | 无参数 |

**理由**：WR 和 CCI 使用 14 周期是业界标准；BIAS 基于 MA20 与布林带中轨一致；OBV 是经典累积量能指标。

### D3: 策略依赖的数据列

| 策略 | 需要的列 | 是否需要前日数据 |
|------|---------|----------------|
| 唐奇安通道突破 | close, high, low（近 20 日） | 是（prev_close vs 通道） |
| ATR 波动率突破 | close, atr14, ma20 | 是（prev_close） |
| CCI 超买超卖 | cci | 是（prev_cci） |
| Williams %R 超卖 | wr | 是（prev_wr） |
| BIAS 乖离率 | bias | 否（单日阈值判断） |
| 缩量回调 | close, vol_ratio, ma20 | 否（单日条件组合） |
| 量价背离 | close, vol（近 20 日） | 是（趋势比较） |
| OBV 突破 | obv, close | 是（prev_obv） |

唐奇安通道和量价背离需要近 N 日窗口数据，在 `filter_batch` 中通过 Pipeline 传入的 DataFrame 获取（Pipeline 已支持前日数据列 `*_prev`）。对于需要更长窗口的策略（如 20 日最高/最低），在策略内部通过额外 SQL 查询或利用已有的 `high`/`low` 历史数据计算。

### D4: 唐奇安通道和量价背离的窗口数据获取

这两个策略需要近 20 日的历史数据来计算通道上下轨或判断趋势。方案：在 `filter_batch` 中接收的 DataFrame 仅包含当日数据和前日数据，不足以计算 20 日窗口。

**方案**：在 `technical_daily` 表新增 `donchian_upper`（Numeric(10,2)）和 `donchian_lower`（Numeric(10,2)）两个预计算字段，在指标计算阶段预先算好 20 日最高价和最低价。这样策略层只需读取预计算值，无需额外查询。

**理由**：与现有指标（如 MA、BOLL）的预计算模式一致，避免策略层做额外数据库查询。

### D5: 文件组织 — 每个策略一个文件

延续现有模式，每个新策略一个独立文件放在 `app/strategy/technical/` 下。

## Risks / Trade-offs

- [新增 6 个字段到 technical_daily] → 表宽度从 23 列增至 29 列，对写入性能影响可忽略（每行增加约 40 字节）。Migration 对已有数据无影响（nullable 字段，默认 NULL）。需要全量重算一次指标以填充新字段。
- [OBV 累积值范围大] → 使用 Numeric(20,2) 存储，最大支持 10^18 级别，足够覆盖 A 股成交量累积。
- [唐奇安通道预计算] → 增加了指标计算的复杂度，但避免了策略层的额外查询，整体更简洁。
- [INDICATOR_COLUMNS 列表需同步更新] → `_build_indicator_row` 和 `_upsert_technical_rows_generic` 依赖此列表，新增字段必须同步添加，否则新指标不会写入数据库。

## Migration Plan

1. 创建 Alembic migration：`technical_daily` 新增 6 个 nullable 字段（wr, cci, bias, obv, donchian_upper, donchian_lower）
2. 更新 `TechnicalDaily` 模型：新增对应 mapped_column
3. 更新 `indicator.py`：新增 4 个计算函数 + 2 个唐奇安通道计算，更新 `INDICATOR_COLUMNS` 和 `compute_indicators_generic`
4. 新增 8 个策略文件 + 注册到 factory
5. 新增单元测试
6. 执行 `alembic upgrade head` + 全量重算指标（`uv run python -m app.data.cli update-indicators`）
7. 回滚策略：`alembic downgrade -1` 删除新字段，删除策略文件和注册项
