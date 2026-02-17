## 1. P2 资金流向数据校验

- [x] 1.1 创建 `tests/integration/test_p2_data_validation.py`，实现 raw_tushare_moneyflow 记录数校验、ETL 字段映射校验、money_flow 关键字段非空率校验、dragon_tiger 数据校验

## 2. P3 指数数据校验

- [x] 2.1 创建 `tests/integration/test_p3_data_validation.py`，实现 raw_tushare_index_daily 核心指数记录校验、index_daily ETL 转换校验、index_weight 权重校验、index_basic 静态数据校验、industry_classify 数据校验

## 3. P4 板块数据校验

- [x] 3.1 创建 `tests/integration/test_p4_data_validation.py`，实现 concept_index 数据校验、concept_daily 记录数校验、concept_member 数据校验、concept_daily ETL 转换校验

## 4. P5 扩展数据校验

- [x] 4.1 创建 `tests/integration/test_p5_data_validation.py`，实现 raw_tushare_suspend_d 数据校验、suspend_info ETL 转换校验、raw_tushare_limit_list_d 数据校验、limit_list_daily ETL 转换校验、P5 日频 raw 表基础校验

## 5. 综合跨表一致性校验

- [x] 5.1 创建 `tests/integration/test_cross_table_validation.py`，实现时间连续性校验、stock_daily 与 index_daily 交易日一致性、stock_daily 与 money_flow 交易日一致性、stocks 表与 stock_daily ts_code 一致性、index_daily 与 index_basic 指数代码一致性、concept_daily 与 concept_index 板块代码一致性、raw_tushare_daily 三表 JOIN 完整性、全链路数据新鲜度校验

## 6. 文档更新

- [x] 6.1 更新 README.md 测试数量和数据校验说明
