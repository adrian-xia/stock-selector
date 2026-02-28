# Pipeline 缓存优化设计文档

> 版本：1.0 | 日期：2026-02-28 | 作者：Kiro

## 1. 背景与问题

### 优化前的性能瓶颈

全市场参数优化器（MarketOptimizer）对每个参数组合都执行完整的 5 层 Pipeline：

```
360 组合 × 15 采样日 = 5400 次完整 Pipeline
每次 Pipeline 处理 5000+ 只股票
总耗时 ≈ 3 小时
```

**核心问题**：Pipeline 的 Layer 1-2（SQL 粗筛、技术面筛选）与策略参数**完全无关**，同一天的结果对所有参数组合都相同，却被重复计算了 360 次。

---

## 2. 架构设计

### 2.1 缓存层级

```
┌─────────────────────────────────────────────────────┐
│                  MarketOptimizer                     │
│                                                      │
│  ① 缓存预热（每个采样日跑一次完整 Pipeline）           │
│     ↓                                                │
│  ② 并发评估参数组合（复用缓存）                        │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│               execute_pipeline()                     │
│                                                      │
│  Layer 1: SQL 粗筛  ──→ pipeline_cache (layer=1)    │
│  Layer 2: 技术面    ──→ pipeline_cache (layer=2)    │
│  Layer 3: 基本面    ──→ 每次重新计算（参数相关）       │
│  Layer 4: 加权排序  ──→ 每次重新计算                  │
│  Layer 5: AI 终审   ──→ 缓存模式下跳过               │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│              pipeline_cache 表（PostgreSQL）          │
│  trade_date + layer + ts_code → passed / raw_data   │
└─────────────────────────────────────────────────────┘
```

### 2.2 数据流

**优化前**：
```
参数组合1 → 完整Pipeline(日期A) → 5000只股票全量计算
参数组合2 → 完整Pipeline(日期A) → 5000只股票全量计算（重复！）
...
参数组合N → 完整Pipeline(日期A) → 5000只股票全量计算（重复！）
```

**优化后**：
```
预热阶段  → 完整Pipeline(日期A) → 写入 pipeline_cache
参数组合1 → 读缓存(日期A L1+L2) → 只算 Layer3-4（~56只股票）
参数组合2 → 读缓存(日期A L1+L2) → 只算 Layer3-4（~56只股票）
...
参数组合N → 读缓存(日期A L1+L2) → 只算 Layer3-4（~56只股票）
```

---

## 3. 数据库表设计

```sql
CREATE TABLE pipeline_cache (
    id BIGSERIAL PRIMARY KEY,
    trade_date DATE NOT NULL,
    layer INT NOT NULL,           -- 1=粗筛, 2=技术面
    ts_code VARCHAR(20) NOT NULL,
    passed BOOLEAN DEFAULT true,  -- 是否通过该层筛选
    raw_data JSONB,               -- 附加数据（Layer 1 存 name）
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (trade_date, layer, ts_code)
);

CREATE INDEX idx_pipeline_cache_date_layer ON pipeline_cache (trade_date, layer);
```

**字段说明**：

| 字段 | 说明 |
|------|------|
| trade_date | 交易日期 |
| layer | 1=Layer1粗筛结果，2=Layer2技术面结果 |
| ts_code | 股票代码 |
| passed | 是否通过该层（Layer2 存所有股票，passed=false 表示被过滤） |
| raw_data | JSONB 附加数据，Layer1 存 `{"name": "股票名称"}` |

---

## 4. 代码改动说明

### 4.1 `app/strategy/pipeline.py`

**新增**：
- `import json` — 用于序列化 raw_data
- `_cache_read_layer(session, trade_date, layer)` — 从 pipeline_cache 读取缓存
- `_cache_write_layer(session, trade_date, layer, records)` — 批量写入缓存

**修改** `execute_pipeline()`：
- 新增参数 `use_cache: bool = False`（默认 False，不影响日常选股）
- `use_cache=True` 时：
  - Layer 1：先查缓存，命中则直接恢复 DataFrame，未命中则计算后写入
  - Layer 2：先查缓存，命中则跳过技术面计算，未命中则计算后写入
  - Layer 3-4：每次重新计算（参数相关）
  - Layer 5 AI：缓存模式下跳过（优化器不需要 AI 评分）
  - 不写入 `strategy_picks` 表（避免污染日常选股数据）

### 4.2 `app/optimization/market_optimizer.py`

**新增** `_warmup_cache(strategy_name, sample_dates)`：
- 对每个采样日并发（最多 4 并发）执行一次完整 Pipeline
- 目的是填充 pipeline_cache，后续参数组合直接复用
- 已有缓存的日期通过 `ON CONFLICT DO NOTHING` 自动跳过

**修改** `optimize()`：
- 在并发评估参数组合前，先调用 `_warmup_cache()` 预热缓存
- 日志标注"缓存模式"

**修改** `_evaluate_params()`：
- 调用 `execute_pipeline()` 时传入 `use_cache=True`

**修改** `__init__()` 默认参数：
- `sample_interval` 默认值从 8 改为 4（配合 config.py 恢复精确采样）

### 4.3 `app/config.py`

| 参数 | 优化前 | 优化后 | 说明 |
|------|--------|--------|------|
| `market_opt_sample_interval` | 8 | 4 | 更精确的采样（缓存后不影响速度） |
| `market_opt_max_combinations` | 200 | 500 | 支持更大参数空间 |
| `market_opt_max_concurrency` | 8 | 8 | 保持不变 |

---

## 5. 性能对比数据

实测环境：5299 只股票，策略 `ma-cross`，日期 2026-02-27

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| 第一次运行（写缓存） | ~32s | ~32s |
| 第二次运行（读缓存） | ~32s | **0.09s** |
| 单日加速比 | 1x | **363x** |
| Layer1 缓存记录 | — | 5299 条 |
| Layer2 缓存记录 | — | 5299 条（56 条 passed=true） |

**整体优化估算**：

```
优化前：360 组合 × 15 天 × 32s = ~48,000s ≈ 13 小时
优化后：15 天预热 × 32s + 360 组合 × 15 天 × 0.09s = 480s + 486s ≈ 16 分钟
实际提速：~45x（含预热开销）
```

> 注：实际提速倍数取决于参数组合数和采样天数，组合数越多收益越大。

---

## 6. 配置参数说明

```python
# app/config.py — Market Optimization 相关配置

market_opt_enabled: bool = True          # 是否启用每周全市场参数优化
market_opt_cron: str = "0 10 * * 6"     # 执行时间（默认周六 10:00）
market_opt_lookback_days: int = 120      # 回看交易日数
market_opt_auto_apply: bool = True       # 完成后是否自动应用最佳参数
market_opt_max_concurrency: int = 8      # 最大并发参数组合数
market_opt_sample_interval: int = 4      # 采样间隔（4=每4天取1天，120天≈30个采样点）
market_opt_max_combinations: int = 500   # 单策略最大参数组合数上限
```

---

## 7. 注意事项

1. **日常选股不受影响**：`execute_pipeline()` 的 `use_cache` 默认为 `False`，所有现有调用路径不变。

2. **缓存污染防护**：`use_cache=True` 模式下不写入 `strategy_picks` 表，避免优化器的历史回放数据污染日常选股记录。

3. **缓存失效**：`pipeline_cache` 表无自动过期机制，历史数据永久保留（数据不变，无需过期）。如需清理可手动执行：
   ```sql
   DELETE FROM pipeline_cache WHERE trade_date < NOW() - INTERVAL '180 days';
   ```

4. **并发安全**：`ON CONFLICT DO NOTHING` 保证多个并发预热任务不会产生冲突。

5. **Redis 热缓存**：当前版本使用 PostgreSQL 持久化缓存，已满足性能需求（363x 加速）。如未来需要进一步优化，可在此基础上叠加 Redis 热缓存层。
