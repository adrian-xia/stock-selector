"""V4 回测 SQL 查询语句。"""

CALC_RETURNS_SQL = """
WITH future AS (
    SELECT sd.ts_code, sd.trade_date, sd.close,
           ROW_NUMBER() OVER (
               PARTITION BY sd.ts_code ORDER BY sd.trade_date
           ) AS day_off
    FROM stock_daily sd
    WHERE sd.ts_code = :code
      AND sd.trade_date > :sig_date
      AND sd.trade_date <= :sig_date + INTERVAL '20 days'
      AND sd.vol > 0
)
SELECT
    MAX(CASE WHEN day_off=1 THEN close END) AS c1,
    MAX(CASE WHEN day_off=3 THEN close END) AS c3,
    MAX(CASE WHEN day_off=5 THEN close END) AS c5,
    MAX(CASE WHEN day_off=10 THEN close END) AS c10
FROM future
"""
