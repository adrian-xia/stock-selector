## 1. 核心计算引擎

- [x] 1.1 创建 `app/data/indicator.py`，实现 `compute_single_stock_indicators(df)` 函数骨架，接收日线 DataFrame 返回含指标列的 DataFrame
- [x] 1.2 实现 MA 计算：MA5/MA10/MA20/MA60/MA120/MA250，使用 `pandas.Series.rolling().mean()`
- [x] 1.3 实现 MACD 计算：EMA(12)、EMA(26)、DIF、DEA(EMA9 of DIF)、HIST(2*(DIF-DEA))，使用 `pandas.Series.ewm().mean()`
- [x] 1.4 实现 KDJ 计算：9日RSV、K/D/J值，处理最高价等于最低价的除零边界
- [x] 1.5 实现 RSI 计算：RSI6/RSI12/RSI24，使用 Wilder 平滑法，处理全涨/全跌边界
- [x] 1.6 实现 Bollinger Bands 计算：BOLL_MID(MA20)、BOLL_UPPER/LOWER(±2σ)，使用 `rolling().std(ddof=0)`
- [x] 1.7 实现成交量指标计算：vol_ma5、vol_ma10、vol_ratio(vol/vol_ma5)，处理 vol_ma5 为零的边界
- [x] 1.8 实现 ATR14 计算：True Range + EMA(14) 平滑

## 2. 批量计算与数据库写入

- [x] 2.1 实现 `compute_all_stocks(session_factory)` 异步函数：查询所有上市股票，逐股加载 300 天日线数据，计算指标，UPSERT 写入 `technical_daily`
- [x] 2.2 实现批量提交逻辑：每 100 只股票 commit 一次，避免长事务；跳过无日线数据的股票
- [x] 2.3 实现 `compute_incremental(session_factory, target_date=None)` 异步函数：确定最新交易日，仅计算并 UPSERT 当日指标行
- [x] 2.4 实现 UPSERT SQL：`INSERT INTO technical_daily ... ON CONFLICT (ts_code, trade_date) DO UPDATE SET ...`，确保幂等写入

## 3. DataManager 查询接口

- [x] 3.1 在 `app/data/manager.py` 的 `DataManager` 类中新增 `get_latest_technical()` 方法：支持按股票代码列表和可选日期查询 `technical_daily`
- [x] 3.2 实现字段选择功能：`fields` 参数控制返回的指标列子集
- [x] 3.3 实现无指定日期时的最新记录查询逻辑：使用子查询获取每只股票的最新 trade_date

## 4. CLI 命令

- [x] 4.1 在 `app/data/cli.py` 中新增 `compute-indicators` 命令：调用 `compute_all_stocks()`，打印汇总结果
- [x] 4.2 在 `app/data/cli.py` 中新增 `update-indicators` 命令：支持 `--date` 参数，调用 `compute_incremental()`，每 500 只股票打印进度日志

## 5. 单元测试

- [x] 5.1 编写 `tests/unit/test_indicator.py`：测试 `compute_single_stock_indicators()` 的各指标计算正确性（MA、MACD、KDJ、RSI、BOLL、vol 指标、ATR）
- [x] 5.2 编写边界测试：空 DataFrame、数据不足的新股、停牌股（vol=0）、价格不变（KDJ 除零）
- [x] 5.3 编写 `tests/unit/test_manager_technical.py`：测试 `get_latest_technical()` 的查询逻辑（含字段选择、空结果）
