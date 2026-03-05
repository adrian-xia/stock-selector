"""过期计划清理 + 极端风险规则引擎。

设计文档 §9.6：每日 Orchestrator 第一步清理过期计划。
设计文档 §6.4：极端风险兜底规则。
"""

import logging
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


async def expire_pending_plans(
    session_factory: async_sessionmaker[AsyncSession],
    today: date,
) -> int:
    """清理过期的 PENDING 计划。

    将 trade_date < today 且 plan_status = 'PENDING' 的计划标记为 EXPIRED。
    设计文档 §9.6。

    Args:
        session_factory: 数据库会话工厂
        today: 当日日期

    Returns:
        清理的计划数
    """
    async with session_factory() as session:
        result = await session.execute(
            text(
                "UPDATE trade_plan_daily_ext "
                "SET plan_status = 'EXPIRED', updated_at = NOW() "
                "WHERE plan_status = 'PENDING' AND trade_date < :today"
            ),
            {"today": today},
        )
        await session.commit()
        count = result.rowcount
        if count > 0:
            logger.info("[规则引擎] 清理过期计划: %d 条", count)
        return count
