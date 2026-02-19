"""实时监控 REST API：监控状态查询、自选股管理。"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.websocket import get_connection_count
from app.config import settings

router = APIRouter(prefix="/api/v1/realtime", tags=["realtime"])

# 全局 RealtimeManager 引用（由 main.py lifespan 注入）
_manager = None


def set_realtime_manager(manager) -> None:
    """设置 RealtimeManager 实例（由 lifespan 调用）。"""
    global _manager
    _manager = manager


# --- Pydantic Schemas ---

class WatchlistRequest(BaseModel):
    ts_codes: list[str]


class StatusResponse(BaseModel):
    collecting: bool
    watchlist_count: int
    watchlist: list[str]
    websocket_connections: int
    max_stocks: int


# --- Endpoints ---

@router.get("/status", response_model=StatusResponse)
async def get_status():
    """获取实时监控状态：采集状态、监控股票数、WebSocket 连接数。"""
    if not _manager:
        return StatusResponse(
            collecting=False,
            watchlist_count=0,
            watchlist=[],
            websocket_connections=get_connection_count(),
            max_stocks=settings.realtime_max_stocks,
        )
    return StatusResponse(
        collecting=_manager.is_running,
        watchlist_count=_manager.watchlist_count,
        watchlist=sorted(_manager.collector.watchlist),
        websocket_connections=get_connection_count(),
        max_stocks=settings.realtime_max_stocks,
    )


@router.post("/watchlist")
async def add_watchlist(body: WatchlistRequest):
    """添加监控股票到自选股列表。"""
    if not _manager:
        raise HTTPException(status_code=503, detail="实时监控未启动")
    added = []
    rejected = []
    for code in body.ts_codes:
        if _manager.collector.add_stock(code):
            added.append(code)
        else:
            rejected.append(code)
    result = {"added": added, "watchlist_count": _manager.watchlist_count}
    if rejected:
        result["rejected"] = rejected
        result["message"] = f"部分股票未添加（超过 {settings.realtime_max_stocks} 只上限）"
    return result


@router.delete("/watchlist")
async def remove_watchlist(body: WatchlistRequest):
    """从自选股列表移除监控股票。"""
    if not _manager:
        raise HTTPException(status_code=503, detail="实时监控未启动")
    for code in body.ts_codes:
        _manager.collector.remove_stock(code)
    return {"removed": body.ts_codes, "watchlist_count": _manager.watchlist_count}
