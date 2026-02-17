"""AI 分析管理器。

编排 AI 分析流程：接收候选股票 → 构建 Prompt → 调用 Gemini → 解析结果 → 输出评分。
V1 使用 Gemini Flash 单模型，失败时静默降级。
支持结果持久化、每日调用上限和 Token 用量记录。
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.ai.clients.gemini import (
    GeminiClient,
    GeminiError,
)
from app.ai.prompts import build_analysis_prompt, get_prompt_version
from app.ai.schemas import AIAnalysisResponse
from app.config import Settings, settings
from app.models.ai import AIAnalysisResult

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.strategy.pipeline import StockPick

logger = logging.getLogger(__name__)


class AIManager:
    """AI 分析编排器。

    延迟初始化 GeminiClient，未配置 API Key 且未启用 ADC 时自动禁用。
    支持结果持久化写入、每日调用上限控制和 Token 用量记录。

    Args:
        ai_settings: 应用配置（包含 Gemini 相关字段）
    """

    def __init__(self, ai_settings: Settings) -> None:
        self._settings = ai_settings
        self._client: GeminiClient | None = None
        self._enabled = bool(ai_settings.gemini_api_key) or bool(ai_settings.gemini_use_adc)

        if not self._enabled:
            logger.warning("AI 分析未启用：GEMINI_API_KEY 未配置且 ADC 未启用")

    @property
    def is_enabled(self) -> bool:
        """AI 分析是否启用。"""
        return self._enabled

    def _get_client(self) -> GeminiClient:
        """延迟初始化并返回 GeminiClient。"""
        if self._client is None:
            self._client = GeminiClient(
                api_key=self._settings.gemini_api_key or None,
                model_id=self._settings.gemini_model_id,
                timeout=self._settings.gemini_timeout,
                max_retries=self._settings.gemini_max_retries,
                use_adc=self._settings.gemini_use_adc,
                gcp_project=self._settings.gemini_gcp_project,
                gcp_location=self._settings.gemini_gcp_location,
            )
        return self._client

    async def _check_daily_limit(self, trade_date: date) -> bool:
        """检查当日 AI 调用是否已达上限。

        基于 Redis 计数，Redis 不可用时放行。

        Returns:
            True 表示可以继续调用，False 表示已达上限
        """
        limit = self._settings.ai_daily_call_limit
        if limit <= 0:
            return True

        try:
            from app.cache.redis_client import get_redis
            redis = await get_redis()
            if redis is None:
                return True

            key = f"ai:daily_calls:{trade_date.isoformat()}"
            count = await redis.get(key)
            if count is not None and int(count) >= limit:
                logger.info("AI 每日调用上限已达 %d/%d，跳过", int(count), limit)
                return False
            return True
        except Exception:
            return True

    async def _incr_daily_count(self, trade_date: date) -> None:
        """递增当日 AI 调用计数。"""
        try:
            from app.cache.redis_client import get_redis
            redis = await get_redis()
            if redis is None:
                return

            key = f"ai:daily_calls:{trade_date.isoformat()}"
            await redis.incr(key)
            await redis.expire(key, 86400 * 2)  # 2 天过期
        except Exception:
            pass


    async def analyze(
        self,
        picks: list[StockPick],
        market_data: dict[str, dict],
        target_date: date,
    ) -> list[StockPick]:
        """对候选股票进行 AI 分析和评分。

        失败时静默降级，返回原始 picks（ai_score 为 None）。

        Args:
            picks: Layer 4 排序后的候选股票
            market_data: ts_code -> 指标数据字典
            target_date: 分析日期

        Returns:
            添加了 AI 评分的 StockPick 列表，按 ai_score 降序排列
        """
        # 未启用或空列表直接返回
        if not self._enabled or not picks:
            return picks

        # 检查每日调用上限
        if not await self._check_daily_limit(target_date):
            return picks

        try:
            # 构建 Prompt
            prompt = build_analysis_prompt(picks, market_data, target_date)

            # 调用 Gemini
            client = self._get_client()
            raw = await client.chat_json(
                prompt, max_tokens=self._settings.gemini_max_tokens
            )

            # 校验响应
            response = AIAnalysisResponse.model_validate(raw)

            # 递增调用计数
            await self._incr_daily_count(target_date)

            # 合并 AI 评分到 picks
            return self._merge_scores(picks, response)

        except GeminiError as exc:
            logger.warning("AI 分析失败，跳过 AI 评分：%s", exc)
            return picks
        except Exception as exc:
            logger.warning("AI 响应解析失败，跳过 AI 评分：%s", exc)
            return picks

    def _merge_scores(
        self,
        picks: list[StockPick],
        response: AIAnalysisResponse,
    ) -> list[StockPick]:
        """将 AI 评分合并到 StockPick 中。"""
        ai_map = {item.ts_code: item for item in response.analysis}

        matched_count = 0
        for pick in picks:
            ai_item = ai_map.get(pick.ts_code)
            if ai_item:
                pick.ai_score = ai_item.score
                pick.ai_signal = ai_item.signal
                pick.ai_summary = ai_item.reasoning
                matched_count += 1

        if matched_count < len(picks):
            logger.warning(
                "AI 返回 %d 条结果，输入 %d 只股票，%d 只未匹配",
                len(response.analysis), len(picks), len(picks) - matched_count,
            )

        picks.sort(key=lambda p: (p.ai_score is not None, p.ai_score or 0), reverse=True)

        logger.info("AI 分析完成：%d/%d 只股票获得评分", matched_count, len(picks))
        return picks


    async def save_results(
        self,
        picks: list[StockPick],
        trade_date: date,
        session_factory: async_sessionmaker[AsyncSession],
        token_usage: dict[str, int] | None = None,
    ) -> int:
        """将 AI 分析结果 UPSERT 到 ai_analysis_results 表。

        Args:
            picks: 带有 AI 评分的候选股票
            trade_date: 分析日期
            session_factory: 数据库会话工厂
            token_usage: Token 用量

        Returns:
            写入的记录数
        """
        # 过滤有 AI 评分的记录
        scored = [p for p in picks if p.ai_score is not None]
        if not scored:
            return 0

        prompt_version = get_prompt_version()
        now = datetime.now()

        rows = [
            {
                "ts_code": p.ts_code,
                "trade_date": trade_date,
                "ai_score": p.ai_score,
                "ai_signal": p.ai_signal or "HOLD",
                "ai_summary": p.ai_summary or "",
                "prompt_version": prompt_version,
                "token_usage": token_usage,
                "created_at": now,
            }
            for p in scored
        ]

        async with session_factory() as session:
            stmt = pg_insert(AIAnalysisResult).values(rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=["ts_code", "trade_date"],
                set_={
                    "ai_score": stmt.excluded.ai_score,
                    "ai_signal": stmt.excluded.ai_signal,
                    "ai_summary": stmt.excluded.ai_summary,
                    "prompt_version": stmt.excluded.prompt_version,
                    "token_usage": stmt.excluded.token_usage,
                    "created_at": stmt.excluded.created_at,
                },
            )
            await session.execute(stmt)
            await session.commit()

        logger.info("[AI结果持久化] %s: %d 条", trade_date, len(rows))
        return len(rows)

    async def get_results(
        self,
        trade_date: date,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> list[dict[str, Any]]:
        """查询指定日期的 AI 分析结果。

        Args:
            trade_date: 查询日期
            session_factory: 数据库会话工厂

        Returns:
            AI 分析结果列表
        """
        async with session_factory() as session:
            stmt = (
                select(AIAnalysisResult)
                .where(AIAnalysisResult.trade_date == trade_date)
                .order_by(AIAnalysisResult.ai_score.desc())
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()

        return [
            {
                "ts_code": r.ts_code,
                "trade_date": r.trade_date.isoformat(),
                "ai_score": r.ai_score,
                "ai_signal": r.ai_signal,
                "ai_summary": r.ai_summary,
                "prompt_version": r.prompt_version,
                "token_usage": r.token_usage,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]


# ---------------------------------------------------------------------------
# 单例
# ---------------------------------------------------------------------------

_ai_manager: AIManager | None = None


def get_ai_manager() -> AIManager:
    """返回延迟初始化的 AIManager 单例。"""
    global _ai_manager
    if _ai_manager is None:
        _ai_manager = AIManager(settings)
    return _ai_manager
