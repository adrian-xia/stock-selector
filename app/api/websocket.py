"""WebSocket 实时行情推送端点。"""

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import settings
from app.realtime.publisher import CHANNEL_PREFIX

logger = logging.getLogger(__name__)
router = APIRouter()

# 全局连接管理
_connections: dict[WebSocket, set[str]] = {}  # ws -> subscribed ts_codes
_redis_listener_task: asyncio.Task | None = None
_redis_client: Any = None


def set_redis_client(client) -> None:
    """设置 Redis 客户端（由 lifespan 调用）。"""
    global _redis_client
    _redis_client = client


async def _redis_listener() -> None:
    """监听 Redis Pub/Sub，转发给对应 WebSocket 客户端。"""
    if not _redis_client:
        return
    pubsub = _redis_client.pubsub()
    await pubsub.psubscribe(f"{CHANNEL_PREFIX}*")
    try:
        async for message in pubsub.listen():
            if message["type"] != "pmessage":
                continue
            channel = message["channel"]
            if isinstance(channel, bytes):
                channel = channel.decode()
            ts_code = channel.replace(CHANNEL_PREFIX, "")
            data = message["data"]
            if isinstance(data, bytes):
                data = data.decode()

            # 推送给订阅了该股票的所有客户端
            for ws, codes in list(_connections.items()):
                if ts_code in codes:
                    try:
                        await ws.send_text(data)
                    except Exception:
                        # 连接已断开，清理
                        _connections.pop(ws, None)
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.punsubscribe()
        await pubsub.close()

async def start_redis_listener() -> None:
    """启动 Redis Pub/Sub 监听任务。"""
    global _redis_listener_task
    if _redis_client and not _redis_listener_task:
        _redis_listener_task = asyncio.create_task(_redis_listener())


async def stop_redis_listener() -> None:
    """停止 Redis Pub/Sub 监听任务。"""
    global _redis_listener_task
    if _redis_listener_task:
        _redis_listener_task.cancel()
        try:
            await _redis_listener_task
        except asyncio.CancelledError:
            pass
        _redis_listener_task = None


@router.websocket("/ws/realtime")
async def websocket_realtime(ws: WebSocket) -> None:
    """实时行情 WebSocket 端点。

    协议：
    - subscribe: {"action": "subscribe", "ts_codes": ["600519.SH", ...]}
    - unsubscribe: {"action": "unsubscribe", "ts_codes": ["600519.SH", ...]}
    """
    await ws.accept()
    _connections[ws] = set()
    logger.info("[WebSocket] 客户端连接，当前连接数: %d", len(_connections))

    try:
        while True:
            try:
                raw = await asyncio.wait_for(ws.receive_text(), timeout=30)
            except asyncio.TimeoutError:
                # 心跳保活
                try:
                    await ws.send_json({"type": "ping"})
                except Exception:
                    break
                continue

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "message": "无效的 JSON"})
                continue

            action = msg.get("action")
            ts_codes = msg.get("ts_codes", [])

            if action == "subscribe":
                current = _connections.get(ws, set())
                if len(current) + len(ts_codes) > settings.realtime_max_stocks:
                    await ws.send_json({
                        "type": "error",
                        "message": f"超过最大监控数量限制 ({settings.realtime_max_stocks})",
                    })
                    continue
                current.update(ts_codes)
                _connections[ws] = current
                await ws.send_json({"type": "subscribed", "ts_codes": list(current)})

            elif action == "unsubscribe":
                current = _connections.get(ws, set())
                current -= set(ts_codes)
                _connections[ws] = current
                await ws.send_json({"type": "unsubscribed", "ts_codes": list(current)})

            else:
                await ws.send_json({"type": "error", "message": f"未知操作: {action}"})

    except WebSocketDisconnect:
        pass
    except Exception:
        logger.warning("[WebSocket] 连接异常", exc_info=True)
    finally:
        _connections.pop(ws, None)
        logger.info("[WebSocket] 客户端断开，当前连接数: %d", len(_connections))


def get_connection_count() -> int:
    """获取当前 WebSocket 连接数。"""
    return len(_connections)

