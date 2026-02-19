"""告警规则与告警历史 REST API。"""

from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import AlertHistory, AlertRule

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


# --- Pydantic Schemas ---

class AlertRuleCreate(BaseModel):
    ts_code: str
    rule_type: str  # price_break / strategy_signal
    params: dict[str, Any] = {}
    cooldown_minutes: int = 30


class AlertRuleUpdate(BaseModel):
    enabled: bool | None = None
    params: dict[str, Any] | None = None
    cooldown_minutes: int | None = None


class AlertRuleResponse(BaseModel):
    id: int
    ts_code: str
    rule_type: str
    params: dict[str, Any]
    enabled: bool
    cooldown_minutes: int
    last_triggered_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertHistoryResponse(BaseModel):
    id: int
    rule_id: int
    ts_code: str
    rule_type: str
    message: str
    notified: bool
    triggered_at: datetime

    model_config = {"from_attributes": True}

async def _get_session():
    """获取数据库会话（由 main.py 注入）。"""
    from app.main import async_session_factory
    async with async_session_factory() as session:
        yield session


@router.post("/rules", response_model=AlertRuleResponse)
async def create_rule(body: AlertRuleCreate, session: AsyncSession = Depends(_get_session)):
    """创建告警规则。"""
    rule = AlertRule(
        ts_code=body.ts_code,
        rule_type=body.rule_type,
        params=body.params,
        cooldown_minutes=body.cooldown_minutes,
    )
    session.add(rule)
    await session.commit()
    await session.refresh(rule)
    return rule


@router.get("/rules", response_model=list[AlertRuleResponse])
async def list_rules(session: AsyncSession = Depends(_get_session)):
    """获取所有告警规则。"""
    result = await session.execute(select(AlertRule).order_by(AlertRule.created_at.desc()))
    return result.scalars().all()


@router.put("/rules/{rule_id}", response_model=AlertRuleResponse)
async def update_rule(rule_id: int, body: AlertRuleUpdate, session: AsyncSession = Depends(_get_session)):
    """更新告警规则。"""
    result = await session.execute(select(AlertRule).where(AlertRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    if body.enabled is not None:
        rule.enabled = body.enabled
    if body.params is not None:
        rule.params = body.params
    if body.cooldown_minutes is not None:
        rule.cooldown_minutes = body.cooldown_minutes
    await session.commit()
    await session.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: int, session: AsyncSession = Depends(_get_session)):
    """删除告警规则。"""
    result = await session.execute(delete(AlertRule).where(AlertRule.id == rule_id))
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="规则不存在")
    await session.commit()
    return {"ok": True}


@router.get("/history", response_model=list[AlertHistoryResponse])
async def list_history(
    ts_code: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(_get_session),
):
    """查询告警历史（分页）。"""
    q = select(AlertHistory).order_by(AlertHistory.triggered_at.desc())
    if ts_code:
        q = q.where(AlertHistory.ts_code == ts_code)
    if start_date:
        q = q.where(AlertHistory.triggered_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        q = q.where(AlertHistory.triggered_at <= datetime.combine(end_date, datetime.max.time()))
    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(q)
    return result.scalars().all()

