"""新闻舆情覆盖范围解析。"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import settings
from app.database import async_session_factory

logger = logging.getLogger(__name__)

NEWS_SCOPE_ALL_MARKET = "all_market"
NEWS_SCOPE_DAILY_CANDIDATES = "daily_candidates"
NEWS_SCOPE_REALTIME_WATCHLIST = "realtime_watchlist"

SUPPORTED_NEWS_SCOPES = {
    NEWS_SCOPE_ALL_MARKET,
    NEWS_SCOPE_DAILY_CANDIDATES,
    NEWS_SCOPE_REALTIME_WATCHLIST,
}


@dataclass(slots=True)
class NewsCoverageUniverse:
    """新闻覆盖股票并集。"""

    ts_codes: list[str]
    requested_scopes: list[str]
    resolved_scopes: list[str]
    code_sources: dict[str, list[str]] = field(default_factory=dict)


def normalize_news_scopes(scopes: list[str] | None = None) -> list[str]:
    """归一化新闻覆盖范围配置。"""
    raw_scopes = scopes if scopes is not None else settings.news_coverage_scopes
    normalized: list[str] = []
    seen: set[str] = set()

    for scope in raw_scopes or [NEWS_SCOPE_DAILY_CANDIDATES]:
        scope_name = scope.strip().lower()
        if not scope_name or scope_name in seen:
            continue
        seen.add(scope_name)
        normalized.append(scope_name)

    if not normalized:
        normalized = [NEWS_SCOPE_DAILY_CANDIDATES]

    return normalized


async def get_latest_news_reference_date(
    session_factory: async_sessionmaker = async_session_factory,
) -> date | None:
    """获取新闻覆盖判断的参考日期。"""
    async with session_factory() as session:
        rows = await session.execute(
            text(
                """
                SELECT
                    (SELECT MAX(pick_date) FROM strategy_picks) AS latest_pick_date,
                    (SELECT MAX(pub_date) FROM announcements) AS latest_pub_date,
                    (SELECT MAX(trade_date) FROM sentiment_daily) AS latest_sentiment_date
                """
            )
        )
        row = rows.first()
        if row is None:
            return None

        candidates = [
            row.latest_pick_date,
            row.latest_pub_date,
            row.latest_sentiment_date,
        ]
        candidates = [d for d in candidates if d is not None]
        return max(candidates) if candidates else None


async def resolve_news_coverage_universe(
    target_date: date | None = None,
    *,
    session_factory: async_sessionmaker = async_session_factory,
    scopes: list[str] | None = None,
    candidate_codes: list[str] | None = None,
) -> NewsCoverageUniverse:
    """解析新闻覆盖股票并集。"""
    requested_scopes = normalize_news_scopes(scopes)
    resolved_scopes: list[str] = []
    source_map: dict[str, set[str]] = {}

    async with session_factory() as session:
        for scope in requested_scopes:
            codes: list[str] = []

            if scope == NEWS_SCOPE_DAILY_CANDIDATES:
                if candidate_codes is not None:
                    codes = [code for code in candidate_codes if code]
                elif target_date is not None:
                    rows = await session.execute(
                        text(
                            """
                            SELECT DISTINCT ts_code
                            FROM strategy_picks
                            WHERE pick_date = :target_date
                            ORDER BY ts_code
                            """
                        ),
                        {"target_date": target_date},
                    )
                    codes = [row.ts_code for row in rows]
                resolved_scopes.append(scope)
            elif scope == NEWS_SCOPE_ALL_MARKET:
                rows = await session.execute(
                    text(
                        """
                        SELECT ts_code
                        FROM stocks
                        WHERE list_status = 'L'
                        ORDER BY ts_code
                        """
                    )
                )
                codes = [row.ts_code for row in rows]
                resolved_scopes.append(scope)
            elif scope == NEWS_SCOPE_REALTIME_WATCHLIST:
                from app.api.realtime import get_watchlist_snapshot

                codes = get_watchlist_snapshot()
                resolved_scopes.append(scope)
            else:
                logger.warning("忽略未知新闻覆盖范围：%s", scope)
                continue

            for code in codes:
                source_map.setdefault(code, set()).add(scope)

    return NewsCoverageUniverse(
        ts_codes=sorted(source_map.keys()),
        requested_scopes=requested_scopes,
        resolved_scopes=resolved_scopes,
        code_sources={code: sorted(sources) for code, sources in source_map.items()},
    )
