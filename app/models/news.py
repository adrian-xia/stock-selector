"""新闻舆情数据库模型：公告和每日情感聚合。"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Announcement(Base):
    """公告/新闻条目表。"""

    __tablename__ = "announcements"
    __table_args__ = (
        UniqueConstraint("ts_code", "source", "title", "pub_date", name="uq_announcement"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts_code: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)  # eastmoney/taoguba/xueqiu
    pub_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sentiment_score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    sentiment_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SentimentDaily(Base):
    """每日情感聚合表。"""

    __tablename__ = "sentiment_daily"
    __table_args__ = (
        UniqueConstraint("ts_code", "trade_date", name="uq_sentiment_daily"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts_code: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    avg_sentiment: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    news_count: Mapped[int] = mapped_column(Integer, default=0)
    positive_count: Mapped[int] = mapped_column(Integer, default=0)
    negative_count: Mapped[int] = mapped_column(Integer, default=0)
    neutral_count: Mapped[int] = mapped_column(Integer, default=0)
    source_breakdown: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
