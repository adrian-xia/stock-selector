"""新闻情感分析器。

复用 GeminiClient 对新闻进行情感打分和分类，支持批量分析和每日聚合。
"""

import json
import logging
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.ai.clients.gemini import GeminiClient, GeminiError
from app.config import settings

logger = logging.getLogger(__name__)

# 加载 Prompt 模板
_PROMPT_PATH = Path(__file__).parent / "prompts" / "news_sentiment_v1.yaml"


def _load_prompt_template() -> dict:
    """加载情感分析 Prompt 模板。"""
    with open(_PROMPT_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


class NewsSentimentAnalyzer:
    """新闻情感分析器。

    使用 Gemini Flash 对新闻进行情感打分，支持批量处理。
    """

    def __init__(self) -> None:
        self._client: GeminiClient | None = None
        self._template = _load_prompt_template()
        self._enabled = bool(settings.gemini_api_key) or bool(settings.gemini_use_adc)

    def _get_client(self) -> GeminiClient:
        if self._client is None:
            self._client = GeminiClient(
                api_key=settings.gemini_api_key or None,
                model_id=settings.gemini_model_id,
                timeout=settings.gemini_timeout,
                max_retries=settings.gemini_max_retries,
                use_adc=settings.gemini_use_adc,
                gcp_project=settings.gemini_gcp_project,
                gcp_location=settings.gemini_gcp_location,
            )
        return self._client

    async def analyze(self, news_items: list[dict]) -> list[dict]:
        """对新闻列表进行情感分析。

        Args:
            news_items: 新闻字典列表，每个包含 ts_code, title, summary

        Returns:
            带有 sentiment_score 和 sentiment_label 的新闻列表
        """
        if not news_items:
            return []

        if not self._enabled:
            logger.warning("AI 未启用，所有新闻标记为中性")
            return [
                {**item, "sentiment_score": 0.0, "sentiment_label": "中性"}
                for item in news_items
            ]

        # 分批处理
        batch_size = settings.news_sentiment_batch_size
        results: list[dict] = []

        for i in range(0, len(news_items), batch_size):
            batch = news_items[i:i + batch_size]
            batch_results = await self._analyze_batch(batch)
            results.extend(batch_results)

        return results

    async def _analyze_batch(self, batch: list[dict]) -> list[dict]:
        """分析一批新闻。"""
        # 构建 Prompt
        news_text = "\n".join(
            f"- [{item['ts_code']}] {item['title']}"
            for item in batch
        )
        user_prompt = self._template["user_prompt_template"].format(
            count=len(batch),
            news_items=news_text,
        )

        try:
            client = self._get_client()
            raw = await client.chat_json(
                prompt=user_prompt,
                system_prompt=self._template.get("system_prompt", ""),
                max_tokens=settings.gemini_max_tokens,
            )

            # 解析结果
            if isinstance(raw, list):
                ai_results = raw
            elif isinstance(raw, dict) and "results" in raw:
                ai_results = raw["results"]
            else:
                ai_results = []

            # 构建结果映射
            ai_map: dict[str, dict] = {}
            for r in ai_results:
                key = f"{r.get('ts_code', '')}_{r.get('title', '')[:50]}"
                ai_map[key] = r

            # 合并回原始数据
            results = []
            for item in batch:
                key = f"{item['ts_code']}_{item['title'][:50]}"
                ai_item = ai_map.get(key, {})
                results.append({
                    **item,
                    "sentiment_score": ai_item.get("sentiment_score", 0.0),
                    "sentiment_label": ai_item.get("sentiment_label", "中性"),
                })
            return results

        except (GeminiError, Exception) as exc:
            logger.warning("情感分析失败，标记为中性: %s", exc)
            return [
                {**item, "sentiment_score": 0.0, "sentiment_label": "中性"}
                for item in batch
            ]


def aggregate_daily_sentiment(
    announcements: list[dict],
    trade_date: date,
) -> list[dict]:
    """聚合每日情感指标。

    Args:
        announcements: 带有 sentiment_score 的公告列表
        trade_date: 交易日期

    Returns:
        每只股票的每日情感聚合数据
    """
    # 按股票分组
    by_stock: dict[str, list[dict]] = defaultdict(list)
    for ann in announcements:
        if ann.get("ts_code"):
            by_stock[ann["ts_code"]].append(ann)

    results = []
    for ts_code, items in by_stock.items():
        scores = [
            item.get("sentiment_score", 0.0)
            for item in items
            if item.get("sentiment_score") is not None
        ]

        avg_score = sum(scores) / len(scores) if scores else 0.0
        positive = sum(1 for s in scores if s > 0.2)
        negative = sum(1 for s in scores if s < -0.2)
        neutral = len(scores) - positive - negative

        # 按来源统计
        source_counts: dict[str, int] = defaultdict(int)
        for item in items:
            source_counts[item.get("source", "unknown")] += 1

        results.append({
            "ts_code": ts_code,
            "trade_date": trade_date,
            "avg_sentiment": round(avg_score, 4),
            "news_count": len(items),
            "positive_count": positive,
            "negative_count": negative,
            "neutral_count": neutral,
            "source_breakdown": dict(source_counts),
        })

    return results


async def save_announcements(
    announcements: list[dict],
    session_factory: async_sessionmaker,
) -> int:
    """批量保存公告到数据库（ON CONFLICT DO NOTHING）。"""
    if not announcements:
        return 0

    async with session_factory() as session:
        for ann in announcements:
            await session.execute(
                text("""
                    INSERT INTO announcements (
                        ts_code, title, summary, source, pub_date, url,
                        sentiment_score, sentiment_label
                    ) VALUES (
                        :ts_code, :title, :summary, :source, :pub_date, :url,
                        :sentiment_score, :sentiment_label
                    )
                    ON CONFLICT ON CONSTRAINT uq_announcement DO NOTHING
                """),
                {
                    "ts_code": ann["ts_code"],
                    "title": ann["title"][:512],
                    "summary": (ann.get("summary") or "")[:1000],
                    "source": ann["source"],
                    "pub_date": ann["pub_date"],
                    "url": ann.get("url"),
                    "sentiment_score": ann.get("sentiment_score"),
                    "sentiment_label": ann.get("sentiment_label"),
                },
            )
        await session.commit()

    logger.info("保存 %d 条公告", len(announcements))
    return len(announcements)


async def save_daily_sentiment(
    daily_data: list[dict],
    session_factory: async_sessionmaker,
) -> int:
    """批量 UPSERT 每日情感聚合数据。"""
    if not daily_data:
        return 0

    async with session_factory() as session:
        for row in daily_data:
            await session.execute(
                text("""
                    INSERT INTO sentiment_daily (
                        ts_code, trade_date, avg_sentiment, news_count,
                        positive_count, negative_count, neutral_count,
                        source_breakdown
                    ) VALUES (
                        :ts_code, :trade_date, :avg_sentiment, :news_count,
                        :positive_count, :negative_count, :neutral_count,
                        CAST(:source_breakdown AS jsonb)
                    )
                    ON CONFLICT ON CONSTRAINT uq_sentiment_daily DO UPDATE SET
                        avg_sentiment = EXCLUDED.avg_sentiment,
                        news_count = EXCLUDED.news_count,
                        positive_count = EXCLUDED.positive_count,
                        negative_count = EXCLUDED.negative_count,
                        neutral_count = EXCLUDED.neutral_count,
                        source_breakdown = EXCLUDED.source_breakdown
                """),
                {
                    "ts_code": row["ts_code"],
                    "trade_date": row["trade_date"],
                    "avg_sentiment": row["avg_sentiment"],
                    "news_count": row["news_count"],
                    "positive_count": row["positive_count"],
                    "negative_count": row["negative_count"],
                    "neutral_count": row["neutral_count"],
                    "source_breakdown": json.dumps(row.get("source_breakdown", {})),
                },
            )
        await session.commit()

    logger.info("保存 %d 条每日情感数据", len(daily_data))
    return len(daily_data)
