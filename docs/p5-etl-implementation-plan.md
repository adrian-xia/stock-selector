# P5 扩展数据 ETL 实施计划（V2）

## 概述

P5 扩展数据包含 48 张 raw 表，分为 6 个子类别。V1 阶段已完成：
- ✅ ORM 模型定义（`app/models/raw.py`）
- ✅ TushareClient fetch 方法（`app/data/tushare.py`）
- ✅ Alembic 迁移脚本（数据库表创建）

V2 阶段待实施：
- ⏸️ ETL 清洗函数（`app/data/etl.py`）
- ⏸️ DataManager 同步方法（`app/data/manager.py`）
- ⏸️ 数据校验测试（`tests/integration/test_p5_data_validation.py`）

## 数据分类

### 11a. 基础数据补充（7 张 raw 表）

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

### 11b. 行情补充（5 张 raw 表）

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

### 11c. 市场参考数据（9 张 raw 表）

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

### 11d. 特色数据（9 张 raw 表）

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

### 11e. 两融数据（4 张 raw 表）

| 表名 | 用途 | 业务表 | ETL 优先级 |
|------|------|--------|-----------|
| raw_tushare_margin | 融资融券汇总 | - | P2 |
| raw_tushare_margin_detail | 融资融券明细 | - | P2 |
| raw_tushare_margin_target | 融资融券标的 | - | P2 |
| raw_tushare_slb_len | 转融通 | - | P3 |

**实施建议：**
- P2 优先：融资融券数据（margin、margin_detail、margin_target，用于市场情绪分析）
- P3 次要：转融通数据

### 11f. 打板专题（14 张 raw 表）

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

## V2 实施路线图

### Phase 1：核心数据（P1 优先级）

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

### Phase 2：增强数据（P2 优先级）

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

### Phase 3：补充数据（P3 优先级）

**目标：** 完善数据体系，支持高级分析

**任务：**
- 其他所有 P3 优先级的表

## ETL 实施模板

### 1. ETL 清洗函数（app/data/etl.py）

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

### 2. DataManager 同步方法（app/data/manager.py）

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

### 3. 数据校验测试（tests/integration/test_p5_data_validation.py）

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

## 注意事项

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

## 参考资料

- Tushare Pro API 文档：https://tushare.pro/document/2
- 设计文档：`docs/design/01-详细设计-数据采集.md`
- V1/V2 划分：`docs/design/99-实施范围-V1与V2划分.md`
