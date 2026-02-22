## ADDED Requirements

### Requirement: K 线图组件
系统 SHALL 提供 KlineChart 组件，基于 ECharts candlestick 图表展示股票 K 线数据。

#### Scenario: 显示 K 线主图和成交量副图
- **WHEN** KlineChart 接收到 K 线数据
- **THEN** SHALL 渲染蜡烛图主图（开盘/收盘/最高/最低）
- **AND** SHALL 在下方渲染成交量柱状副图
- **AND** 涨（收盘>开盘）SHALL 显示红色，跌 SHALL 显示绿色

#### Scenario: 均线叠加显示
- **WHEN** K 线图渲染完成
- **THEN** SHALL 叠加显示 MA5、MA10、MA20 三条均线
- **AND** 每条均线 SHALL 使用不同颜色区分

#### Scenario: 日期范围缩放
- **WHEN** 用户操作 dataZoom 滑块
- **THEN** SHALL 同步缩放 K 线主图和成交量副图的日期范围

#### Scenario: 默认数据范围
- **WHEN** K 线图首次加载
- **THEN** SHALL 默认请求最近 120 个交易日的数据
- **AND** 数据 SHALL 通过 React Query 管理（缓存 + 加载状态）

### Requirement: StockDetail 集成 K 线图
StockDetail 组件 SHALL 集成 KlineChart，展示选中股票的 K 线走势。

#### Scenario: 选中股票后显示 K 线
- **WHEN** 用户在选股结果中点击某只股票
- **THEN** StockDetail SHALL 显示该股票的 K 线图
- **AND** K 线数据 SHALL 通过 `api/data.ts` 的 fetchKline 获取
