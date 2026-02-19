## Context

当前系统仅支持盘后批处理：每日收盘后自动同步数据、计算指标、执行策略、AI 分析。前端通过轮询获取结果。V1 的 NotificationManager 仅记录日志，不接入实际通知服务。

概要设计模块 10 规划了完整的实时监控与告警系统，包括 WebSocket 实时推送、告警规则引擎、防抖动机制和多渠道通知。缓存策略文档已预留 Redis key 模式（`market:realtime:*`、`alert:cooldown:*`、`ws:subscribers:*`）。

## Goals / Non-Goals

**Goals:**
- 盘中实时采集自选股行情数据（Tushare Pro），通过 WebSocket 推送到前端
- 提供告警规则引擎，支持价格预警和策略信号预警
- 告警触发后通过企业微信 Webhook / Telegram Bot 发送通知
- 前端新增实时监控看板页面

**Non-Goals:**
- 不做全市场实时行情（仅监控用户自选股，上限 50 只）
- 不做高频交易级别的低延迟（目标 < 500ms，非微秒级）
- 不做舆情实时预警（已有盘后新闻情感分析）
- 不做短信通知（成本高，企业微信/Telegram 足够）
- 不做移动端推送

## Decisions

### D1: 实时行情数据源 — Tushare Pro 轮询

**选择**：复用 TushareClient，调用实时行情相关接口（如 `realtime_quote` 或 `daily` 当日数据），后端定时轮询（每 3 秒）
**替代方案**：AKShare（已从项目中移除）、直接 WebSocket 接入交易所（合规风险）
**理由**：项目已统一使用 Tushare Pro 作为唯一数据源，复用现有 TushareClient 和令牌桶限流，无需引入新依赖

### D2: 数据分发 — Redis Pub/Sub

**选择**：行情数据通过 Redis Pub/Sub 分发，channel 格式 `market:realtime:{ts_code}`
**替代方案**：直接内存队列（不支持多进程）、Kafka（过重）
**理由**：项目已依赖 Redis，Pub/Sub 轻量且支持多订阅者，与现有缓存基础设施一致

### D3: WebSocket 架构 — FastAPI 原生

**选择**：FastAPI 内置 WebSocket 支持，单进程管理连接
**替代方案**：独立 WebSocket 服务（Socket.IO）、SSE（Server-Sent Events）
**理由**：单机单用户场景，FastAPI 原生 WebSocket 足够，无需额外依赖。SSE 不支持双向通信（无法动态订阅/取消）

### D4: 告警防抖动 — Redis 冷却标记

**选择**：告警触发后在 Redis 设置冷却 key（`alert:cooldown:{ts_code}:{rule_type}`），TTL 为冷却时间
**理由**：利用 Redis TTL 自动过期，无需定时清理，实现简单可靠

### D5: 通知渠道 — 企业微信 + Telegram

**选择**：扩展现有 NotificationManager，新增 WeComChannel 和 TelegramChannel
**理由**：企业微信覆盖国内用户，Telegram 覆盖海外/技术用户，两者均通过 Webhook/Bot API 实现，无需 SDK

### D6: 实时指标计算 — 增量计算

**选择**：盘中每分钟对监控股票计算关键技术指标（MA、MACD、RSI），基于最新行情 + 历史数据增量计算
**替代方案**：全量重算（浪费资源）
**理由**：监控股票上限 50 只，增量计算性能开销可控

### D7: 数据库表设计

新增 2 张表：
- `alert_rules`：用户配置的告警规则（ts_code、rule_type、params、enabled、cooldown_minutes）
- `alert_history`：已触发的告警记录（rule_id、ts_code、triggered_at、message、notified）

## Risks / Trade-offs

- **Tushare API 限流** → 复用现有令牌桶限流（400 QPS），实时轮询 50 只股票每 3 秒一次，QPS 开销极低
- **Redis Pub/Sub 消息丢失** → 单机单用户场景可接受，前端重连后自动获取最新快照
- **盘中资源占用** → 仅在交易时段（9:15-15:00）启动实时采集，非交易时段自动停止
- **轮询延迟** → 轮询模式有 3 秒延迟，对个人投资者可接受
