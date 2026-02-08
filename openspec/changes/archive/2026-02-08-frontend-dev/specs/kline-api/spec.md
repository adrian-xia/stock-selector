## ADDED Requirements

### Requirement: K 线数据查询接口
系统 SHALL 提供 `GET /api/v1/data/kline/{ts_code}` 接口，从 `stock_daily` 表查询指定股票的日 K 线数据（OHLCV），支持 `start_date`、`end_date`、`limit` 参数。

#### Scenario: 查询指定股票 K 线
- **WHEN** 请求 `GET /api/v1/data/kline/600519.SH?limit=120`
- **THEN** 返回最近 120 个交易日的 K 线数据，按日期升序排列

#### Scenario: 指定日期范围查询
- **WHEN** 请求 `GET /api/v1/data/kline/600519.SH?start_date=2025-01-01&end_date=2025-12-31`
- **THEN** 返回该日期范围内的 K 线数据

#### Scenario: 股票不存在或无数据
- **WHEN** 请求的 ts_code 不存在或无日线数据
- **THEN** 返回空数组，HTTP 200

### Requirement: K 线响应格式
系统 SHALL 返回以下 JSON 格式：`{ "ts_code": "600519.SH", "data": [{ "date": "2025-01-02", "open": 1680.0, "high": 1700.0, "low": 1675.0, "close": 1695.0, "volume": 12345 }] }`。

#### Scenario: 响应字段完整
- **WHEN** K 线查询返回数据
- **THEN** 每条记录包含 date、open、high、low、close、volume 六个字段

### Requirement: CORS 配置
系统 SHALL 在 FastAPI 应用中配置 CORSMiddleware，允许 `http://localhost:5173`（Vite 开发服务器）的跨域请求。

#### Scenario: 前端开发服务器跨域请求
- **WHEN** 前端从 `localhost:5173` 发送 API 请求到 `localhost:8000`
- **THEN** 后端返回正确的 CORS 头，请求成功
