"""新闻舆情 HTTP API。

提供新闻列表查询、情感趋势查询和每日情感摘要端点。
"""

import logging
from datetime import date

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.database import async_session_factory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/news", tags=["news"])


# ---------------------------------------------------------------------------
# Pydantic 请求/响应模型
# ---------------------------------------------------------------------------

class AnnouncementItem(BaseModel):
    """单条公告。"""
    id: int
    ts_code: str
    title: str
    summary: str | None = None
    source: str
    pub_date: date
    url: str | None = None
    sentiment_score: float | None = None
    sentiment_label: str | None = None


class NewsListResponse(BaseModel):
    """新闻列表响应。"""
    total: int
    page: int
    page_size: int
    items: list[AnnouncementItem]


class SentimentTrendItem(BaseModel):
    """单日情感趋势数据点。"""
    trade_date: date
    avg_sentiment: float
    news_count: int
    positive_count: int
    negative_count: int
    neutral_count: int


class SentimentSummaryItem(BaseModel):
    """单只股票的每日情感摘要。"""
    ts_code: str
    avg_sentiment: float
    news_count: int
    positive_count: int
    negative_count: int
    neutral_count: int
    source_breakdown: dict | None = None


class SentimentSummaryResponse(BaseModel):
    """情感摘要响应。"""
    trade_date: date | None
    items: list[SentimentSummaryItem]


# ---------------------------------------------------------------------------
# 端点
# ---------------------------------------------------------------------------

@router.get("/list", response_model=NewsListResponse)
async def get_news_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    ts_code: str | None = Query(None, description="股票代码筛选"),
    source: str | None = Query(None, description="来源筛选"),
    start_date: date | None = Query(None, description="开始日期"),
    end_date: date | None = Query(None, description="结束日期"),
) -> NewsListResponse:
    """分页查询新闻列表，支持按股票代码、来源、日期筛选。"""
    conditions: list[str] = []
    params: dict = {}

    if ts_code:
        conditions.append("ts_code = :ts_code")
        params["ts_code"] = ts_code
    if source:
        conditions.append("source = :source")
        params["source"] = source
    if start_date:
        conditions.append("pub_date >= :start_date")
        params["start_date"] = start_date
    if end_date:
        conditions.append("pub_date <= :end_date")
        params["end_date"] = end_date

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    offset = (page - 1) * page_size

    async with async_session_factory() as session:
        # 总数
        count_row = await session.execute(
            text(f"SELECT COUNT(*) FROM announcements WHERE {where_clause}"),
            params,
        )
        total = count_row.scalar() or 0

        # 分页数据
        rows = await session.execute(
            text(
                f"SELECT id, ts_code, title, summary, source, pub_date, url, "
                f"sentiment_score, sentiment_label "
                f"FROM announcements WHERE {where_clause} "
                f"ORDER BY pub_date DESC, id DESC "
                f"LIMIT :limit OFFSET :offset"
            ),
            {**params, "limit": page_size, "offset": offset},
        )
        items = [
            AnnouncementItem(
                id=r.id, ts_code=r.ts_code, title=r.title,
                summary=r.summary, source=r.source, pub_date=r.pub_date,
                url=r.url, sentiment_score=r.sentiment_score,
                sentiment_label=r.sentiment_label,
            )
            for r in rows
        ]

    return NewsListResponse(total=total, page=page, page_size=page_size, items=items)


@router.get("/sentiment-trend/{ts_code}", response_model=list[SentimentTrendItem])
async def get_sentiment_trend(
    ts_code: str,
    days: int = Query(30, ge=1, le=365, description="查询天数"),
) -> list[SentimentTrendItem]:
    """查询指定股票的情感趋势（按日期升序）。"""
    async with async_session_factory() as session:
        rows = await session.execute(
            text(
                "SELECT trade_date, avg_sentiment, news_count, "
                "positive_count, negative_count, neutral_count "
                "FROM sentiment_daily "
                "WHERE ts_code = :ts_code "
                "ORDER BY trade_date DESC LIMIT :days"
            ),
            {"ts_code": ts_code, "days": days},
        )
        items = [
            SentimentTrendItem(
                trade_date=r.trade_date, avg_sentiment=r.avg_sentiment,
                news_count=r.news_count, positive_count=r.positive_count,
                negative_count=r.negative_count, neutral_count=r.neutral_count,
            )
            for r in rows
        ]
    # 返回按日期升序
    items.reverse()
    return items


@router.get("/sentiment-summary", response_model=SentimentSummaryResponse)
async def get_sentiment_summary(
    trade_date: date | None = Query(None, description="交易日期（默认最新）"),
    top_n: int = Query(20, ge=1, le=100, description="返回前 N 只"),
) -> SentimentSummaryResponse:
    """查询每日情感摘要：按 news_count 降序返回 Top N 股票。"""
    async with async_session_factory() as session:
        # 如果未指定日期，取最新日期
        if trade_date is None:
            latest = await session.execute(
                text("SELECT MAX(trade_date) FROM sentiment_daily")
            )
            trade_date = latest.scalar()
            if trade_date is None:
                return SentimentSummaryResponse(trade_date=None, items=[])

        rows = await session.execute(
            text(
                "SELECT ts_code, avg_sentiment, news_count, "
                "positive_count, negative_count, neutral_count, source_breakdown "
                "FROM sentiment_daily "
                "WHERE trade_date = :trade_date "
                "ORDER BY news_count DESC LIMIT :top_n"
            ),
            {"trade_date": trade_date, "top_n": top_n},
        )
        items = [
            SentimentSummaryItem(
                ts_code=r.ts_code, avg_sentiment=r.avg_sentiment,
                news_count=r.news_count, positive_count=r.positive_count,
                negative_count=r.negative_count, neutral_count=r.neutral_count,
                source_breakdown=r.source_breakdown,
            )
            for r in rows
        ]

    return SentimentSummaryResponse(trade_date=trade_date, items=items)
