## 0. 遗留数据源清理（BaoStock/AKShare → Tushare）

- [x] 0.1 清理 `app/models/` 中 `data_source` 默认值：market.py、finance.py、flow.py 从 baostock/akshare 改为 tushare
- [x] 0.2 清理 `app/data/etl.py`：移除 `normalize_stock_code` 中 baostock/akshare 死代码分支
- [x] 0.3 清理 `app/data/tushare.py`、`app/data/adj_factor.py` 注释中的 BaoStock 引用
- [x] 0.4 清理 `tests/unit/` 6 个测试文件的 mock client 从 baostock 改为 tushare，更新 test_etl.py 测试用例
- [x] 0.5 删除无法运行的旧脚本：quick_verify_batch_sync.py、verify_batch_sync_performance.py、verify_core_functionality.py、test_data_integrity.py、verify_scheduler.md、PERFORMANCE_VERIFICATION.md
- [x] 0.6 删除无法运行的旧集成测试：test_daily_sync_performance.py
- [x] 0.7 清理 `README.md`：移除 BaoStock 连接池关闭步骤，更新目录结构
- [x] 0.8 清理 `PROJECT_TASKS.md`、`docs/用户指南.md` 中的 AKShare/BaoStock 引用
- [x] 0.9 清理 `openspec/specs/` 13 个 spec 文件中的 BaoStock/AKShare 引用
- [x] 0.10 修正 realtime-monitor openspec artifacts（proposal/design/specs/tasks）中 AKShare → Tushare Pro

## 1. 基础设施

- [x] 1.1 新增配置项到 `app/config.py`：`WECOM_WEBHOOK_URL`、`TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID`、`REALTIME_POLL_INTERVAL`（默认 3）、`REALTIME_MAX_STOCKS`（默认 50）
- [x] 1.2 更新 `.env.example` 添加新配置项
- [x] 1.3 创建 Alembic 迁移：新增 `alert_rules` 和 `alert_history` 表
- [x] 1.4 创建 ORM 模型 `app/models/alert.py`：`AlertRule`、`AlertHistory`

## 2. 实时行情采集

- [x] 2.1 创建 `app/realtime/__init__.py` 模块
- [x] 2.2 创建 `app/realtime/collector.py`：基于 TushareClient 的行情采集器，定时轮询（每 3 秒），交易时段判断（9:15-15:00），连续失败 3 次暂停 1 分钟重试
- [x] 2.3 创建 `app/realtime/publisher.py`：Redis Pub/Sub 发布器，将行情数据发布到 `market:realtime:{ts_code}` channel
- [x] 2.4 创建 `app/realtime/manager.py`：RealtimeManager 统一管理采集生命周期（start/stop），交易时段自动启停

## 3. WebSocket 服务

- [x] 3.1 创建 `app/api/websocket.py`：WebSocket 端点 `/ws/realtime`
- [x] 3.2 实现订阅/取消订阅协议（subscribe/unsubscribe 消息，50 只上限校验）
- [x] 3.3 实现 Redis Pub/Sub 订阅转发：监听 `market:realtime:*` channel，推送给对应 WebSocket 客户端
- [x] 3.4 实现心跳保活（30 秒无数据发送 ping）和断连清理

## 4. 实时指标计算

- [x] 4.1 创建 `app/realtime/indicator.py`：盘中增量指标计算（MA5/10/20、MACD、RSI），每 60 秒执行
- [x] 4.2 实现信号检测逻辑：MA 金叉/死叉、RSI 超买/超卖，检测到信号后发送告警事件

## 5. 告警规则引擎

- [x] 5.1 创建 `app/realtime/alert_engine.py`：告警规则评估器，从数据库加载 enabled 规则，评估价格预警和策略信号
- [x] 5.2 实现防抖动冷却机制：Redis key `alert:cooldown:{ts_code}:{rule_id}` + TTL，默认 30 分钟
- [x] 5.3 实现告警触发流程：写入 alert_history → 调用通知分发

## 6. 通知渠道

- [x] 6.1 扩展 `app/notification/__init__.py`：新增 `WeComChannel`（企业微信 Webhook，POST markdown 消息）
- [x] 6.2 新增 `TelegramChannel`（Telegram Bot API sendMessage）
- [x] 6.3 更新 `NotificationManager`：根据配置自动注册可用渠道，告警触发时遍历渠道发送，失败记日志不重试

## 7. REST API

- [x] 7.1 创建 `app/api/alert.py`：告警规则 CRUD 端点（POST/GET/PUT/DELETE /api/alerts/rules）
- [x] 7.2 新增告警历史查询端点（GET /api/alerts/history，支持 ts_code 和日期范围过滤，分页）
- [x] 7.3 新增监控状态端点（GET /api/realtime/status，返回采集状态、监控股票数、WebSocket 连接数）
- [x] 7.4 新增自选股管理端点（POST/DELETE /api/realtime/watchlist，添加/移除监控股票）
- [x] 7.5 在 `app/main.py` 注册新路由

## 8. 前端实时监控看板

- [x] 8.1 创建 `web/src/hooks/useWebSocket.ts`：WebSocket 连接 hook（自动重连、订阅管理）
- [x] 8.2 创建 `web/src/pages/monitor/` 页面目录和路由注册
- [x] 8.3 实现自选股行情表格组件：实时价格、涨跌幅、成交量，价格变动闪烁效果（绿涨红跌）
- [x] 8.4 实现自选股管理：搜索添加、移除、50 只上限提示
- [x] 8.5 实现信号指示器组件：策略信号 badge 显示（MA金叉、RSI超卖等），60 分钟过期淡化
- [x] 8.6 实现告警历史面板：最近 20 条告警，新告警 Ant Design notification 弹窗
- [x] 8.7 实现告警规则管理 modal：创建规则（类型选择、参数配置、冷却时间）、规则列表开关
- [x] 8.8 实现连接状态指示器：WebSocket 断连时显示"连接断开"banner，5 秒自动重连

## 9. 生命周期集成

- [x] 9.1 在 `app/main.py` lifespan 中集成 RealtimeManager 启停（startup 启动采集，shutdown 优雅关闭）
- [x] 9.2 添加侧边栏导航项"实时监控"

## 10. 单元测试

- [x] 10.1 测试行情采集器：mock TushareClient，验证轮询逻辑、交易时段判断、失败重试
- [x] 10.2 测试告警规则引擎：价格预警触发、策略信号触发、冷却机制
- [x] 10.3 测试通知渠道：mock HTTP 请求，验证企业微信/Telegram 消息格式
- [x] 10.4 测试 WebSocket 端点：订阅/取消订阅、上限校验、断连清理
- [x] 10.5 测试告警 API：CRUD 操作、历史查询分页

## 11. 文档更新

- [x] 11.1 更新 `docs/design/99-实施范围-V1与V2划分.md`，标注实时监控已实施
- [x] 11.2 更新 `README.md`
- [x] 11.3 更新 `CLAUDE.md`
- [x] 11.4 更新 `PROJECT_TASKS.md`，标记 Change 12 为已完成
