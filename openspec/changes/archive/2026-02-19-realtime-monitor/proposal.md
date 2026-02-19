## Why

当前系统仅支持盘后批处理分析，投资者无法在盘中实时跟踪自选股动态和策略信号触发。实时监控与告警是 V2 规划的核心模块（概要设计模块 10），补全盘中场景后可形成"盘中监控 + 盘后分析"的完整投资工作流。

## What Changes

- **新增 WebSocket 服务**：基于 FastAPI WebSocket，支持客户端订阅自选股实时行情推送，心跳保活
- **新增实时行情采集**：复用 Tushare Pro 实时行情接口，定时轮询（每 3 秒），通过 Redis Pub/Sub 分发
- **新增实时指标计算**：盘中每分钟计算技术指标，检测策略信号触发，生成告警事件
- **新增告警规则引擎**：支持价格预警、策略信号预警两种规则类型，用户可配置规则，含防抖动冷却机制
- **新增通知渠道**：扩展现有 NotificationManager，接入企业微信 Webhook 和 Telegram Bot（V1 仅日志）
- **新增数据库表**：alert_rules（告警规则）、alert_history（告警记录）
- **新增前端页面**：实时监控看板（自选股行情、信号提示、告警历史）

## Capabilities

### New Capabilities
- `realtime-quote`: 实时行情采集与 WebSocket 推送，包括 Tushare 实时行情接口、Redis Pub/Sub 分发、WebSocket 订阅协议
- `alert-engine`: 告警规则引擎，包括规则配置、信号检测、防抖动冷却、通知分发
- `monitor-dashboard`: 前端实时监控看板，包括 WebSocket 集成、自选股行情展示、告警历史

### Modified Capabilities
（无现有 spec 需要修改）

## Impact

- **后端新增模块**：`app/realtime/`（行情采集 + 指标计算）、`app/api/websocket.py`
- **扩展现有模块**：`app/notification/`（新增企业微信/Telegram 渠道）
- **新增依赖**：无新增（复用 Tushare Pro，websockets 已随 FastAPI 安装）
- **数据库**：新增 2 张表（alert_rules、alert_history）+ Alembic 迁移
- **Redis**：新增 Pub/Sub channel（`market:realtime:{ts_code}`）和冷却标记 key
- **前端**：新增监控看板页面 + WebSocket 客户端 hook
- **性能约束**：盘中监控股票上限 50 只，行情处理延迟 < 500ms
