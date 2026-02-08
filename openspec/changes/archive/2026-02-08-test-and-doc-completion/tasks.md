## 1. 策略 API 测试

- [x] 1.1 创建 `tests/unit/test_api_strategy.py`，测试 POST /strategy/run 正常执行（mock execute_pipeline）
- [x] 1.2 测试 POST /strategy/run 无效策略名称返回 400
- [x] 1.3 测试 GET /strategy/list 返回全部策略
- [x] 1.4 测试 GET /strategy/list 按 category 过滤
- [x] 1.5 测试 GET /strategy/schema/{name} 查询存在的策略
- [x] 1.6 测试 GET /strategy/schema/{name} 查询不存在的策略返回 404

## 2. 回测 API 测试

- [x] 2.1 创建 `tests/unit/test_api_backtest_run.py`，测试 POST /backtest/run 正常执行（mock run_backtest + writer）
- [x] 2.2 测试 POST /backtest/run 日期范围无效返回 400
- [x] 2.3 测试 POST /backtest/run 回测执行失败返回 status="failed"
- [x] 2.4 测试 GET /backtest/result/{task_id} 查询已完成任务（含 metrics、trades、equity_curve）
- [x] 2.5 测试 GET /backtest/result/{task_id} 查询不存在的任务返回 404
- [x] 2.6 测试 GET /backtest/result/{task_id} 查询运行中的任务
- [x] 2.7 测试 GET /backtest/result/{task_id} 查询失败的任务

## 3. 回测策略基类测试

- [x] 3.1 创建 `tests/unit/test_backtest_strategy.py`，测试 AStockStrategy 涨停拦截买入
- [x] 3.2 测试 AStockStrategy 正常买入
- [x] 3.3 测试 AStockStrategy 跌停拦截卖出
- [x] 3.4 测试 AStockStrategy 净值曲线记录（equity_curve 长度和结构）
- [x] 3.5 测试 AStockStrategy 交易日志记录（trades_log 结构）
- [x] 3.6 测试 SignalStrategy 首日买入（100 股整数倍）
- [x] 3.7 测试 SignalStrategy 持有天数到期卖出
- [x] 3.8 测试 SignalStrategy 止损卖出
- [x] 3.9 测试 SignalStrategy 停牌日不操作

## 4. 回测数据加载测试

- [x] 4.1 创建 `tests/unit/test_backtest_data_feed.py`，测试 load_stock_data 正常加载并验证前复权公式
- [x] 4.2 测试 load_stock_data 无数据返回空 DataFrame
- [x] 4.3 测试 build_data_feed 字段映射正确

## 5. BaoStock 客户端测试

- [x] 5.1 创建 `tests/unit/test_baostock_client.py`，测试标准代码转 BaoStock 格式（SH/SZ）
- [x] 5.2 测试 BaoStock 格式转标准代码
- [x] 5.3 测试日线数据解析
- [x] 5.4 测试重试机制
- [x] 5.5 测试健康检查

## 6. AKShare 客户端测试

- [x] 6.1 创建 `tests/unit/test_akshare_client.py`，测试交易所推断（SH/SZ）
- [x] 6.2 测试 Decimal 转换处理 NaN
- [x] 6.3 测试日线数据解析
- [x] 6.4 测试重试机制
- [x] 6.5 测试股票列表获取

## 7. 文档更新

- [x] 7.1 更新 README.md 补充 API 端点列表（7 个端点）
- [x] 7.2 更新 README.md 测试数量统计
- [x] 7.3 运行全部测试确认通过，更新最终测试数量
