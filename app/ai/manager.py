"""AI 分析管理器。

编排 AI 分析流程：接收候选股票 → 构建 Prompt → 调用 Gemini → 解析结果 → 输出评分。
V1 使用 Gemini Flash 单模型，失败时静默降级。
"""

from __future__ import annotations

import logging
from datetime import date
from typing import TYPE_CHECKING

from app.ai.clients.gemini import (
    GeminiClient,
    GeminiError,
)
from app.ai.prompts import build_analysis_prompt
from app.ai.schemas import AIAnalysisResponse
from app.config import Settings, settings

if TYPE_CHECKING:
    from app.strategy.pipeline import StockPick

logger = logging.getLogger(__name__)


class AIManager:
    """AI 分析编排器。

    延迟初始化 GeminiClient，未配置 API Key 且未启用 ADC 时自动禁用。

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
            )
        return self._client

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
        """将 AI 评分合并到 StockPick 中。

        处理部分响应：AI 返回数量不匹配时，未匹配的股票 ai_score 保持 None。
        """
        # 构建 ts_code -> AI 结果映射
        ai_map = {item.ts_code: item for item in response.analysis}

        matched_count = 0
        for pick in picks:
            ai_item = ai_map.get(pick.ts_code)
            if ai_item:
                pick.ai_score = ai_item.score
                pick.ai_signal = ai_item.signal
                pick.ai_summary = ai_item.reasoning
                matched_count += 1

        # 检查数量是否匹配
        if matched_count < len(picks):
            logger.warning(
                "AI 返回 %d 条结果，输入 %d 只股票，%d 只未匹配",
                len(response.analysis), len(picks), len(picks) - matched_count,
            )

        # 按 ai_score 降序排序，None 排最后
        picks.sort(key=lambda p: (p.ai_score is not None, p.ai_score or 0), reverse=True)

        logger.info(
            "AI 分析完成：%d/%d 只股票获得评分",
            matched_count, len(picks),
        )
        return picks


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
