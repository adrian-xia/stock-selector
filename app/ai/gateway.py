"""统一 AI 网关。

当前仅保留 Codex 实现，对外提供统一的文本 / JSON 生成接口。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Literal

from app.ai.clients.codex import CodexClient, CodexError
from app.config import Settings, settings

logger = logging.getLogger(__name__)

ResponseFormat = Literal["text", "json"]


@dataclass(slots=True)
class AIRequest:
    """统一 AI 请求。"""

    prompt: str
    task_name: str = "general"
    response_format: ResponseFormat = "text"
    system_prompt: str = ""
    max_tokens: int | None = None


@dataclass(slots=True)
class AIResponse:
    """统一 AI 响应。"""

    ok: bool
    provider: str
    task_name: str
    content: Any | None = None
    token_usage: dict[str, int] = field(default_factory=dict)
    error: str | None = None


class AIGateway:
    """统一 AI 网关。"""

    def __init__(self, ai_settings: Settings) -> None:
        self._settings = ai_settings
        self._provider = ai_settings.ai_provider.lower()
        self._client: CodexClient | None = None

        if self._provider in ("", "none"):
            self._enabled = False
        elif self._provider != "codex":
            self._enabled = False
            logger.warning("AI 网关未启用：仅支持 AI_PROVIDER=codex，当前为 %s", self._provider)
        else:
            self._enabled = bool(ai_settings.codex_api_key)
            if not self._enabled:
                logger.warning("AI 网关未启用：CODEX_API_KEY 未配置")

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    @property
    def provider(self) -> str:
        return self._provider

    def _get_client(self) -> CodexClient:
        if self._client is None:
            if self._provider != "codex":
                raise ValueError(f"不支持的 AI 提供商: {self._provider}")
            self._client = CodexClient(
                api_key=self._settings.codex_api_key,
                base_url=self._settings.codex_base_url,
                model_id=self._settings.codex_model_id,
                timeout=self._settings.codex_timeout,
                max_retries=self._settings.codex_max_retries,
                thinking_default=self._settings.codex_thinking_default,
            )
        return self._client

    def get_last_usage(self) -> dict[str, int]:
        if self._client and hasattr(self._client, "get_last_usage"):
            return self._client.get_last_usage()
        return {}

    def _resolve_max_tokens(self, override: int | None) -> int:
        if override is not None:
            return override
        return self._settings.codex_max_tokens

    @staticmethod
    def _compose_prompt(system_prompt: str, prompt: str) -> str:
        if not system_prompt.strip():
            return prompt
        return (
            f"【系统指令】\n{system_prompt.strip()}\n\n"
            f"【用户任务】\n{prompt.strip()}"
        )

    async def execute(self, request: AIRequest) -> AIResponse:
        """执行统一 AI 请求。"""
        if not self._enabled:
            return AIResponse(
                ok=False,
                provider=self._provider,
                task_name=request.task_name,
                error="ai_disabled",
            )

        try:
            client = self._get_client()
            final_prompt = self._compose_prompt(request.system_prompt, request.prompt)
            max_tokens = self._resolve_max_tokens(request.max_tokens)

            if request.response_format == "json":
                content = await client.chat_json(final_prompt, max_tokens=max_tokens)
            else:
                content = await client.chat(final_prompt, max_tokens=max_tokens)

            return AIResponse(
                ok=True,
                provider=self._provider,
                task_name=request.task_name,
                content=content,
                token_usage=self.get_last_usage(),
            )
        except (CodexError, ValueError) as exc:
            logger.warning(
                "AI 网关调用失败：task=%s provider=%s error=%s",
                request.task_name, self._provider, exc,
            )
            return AIResponse(
                ok=False,
                provider=self._provider,
                task_name=request.task_name,
                error=str(exc),
            )
        except Exception as exc:
            logger.warning(
                "AI 网关调用异常：task=%s provider=%s error=%s",
                request.task_name, self._provider, exc,
            )
            return AIResponse(
                ok=False,
                provider=self._provider,
                task_name=request.task_name,
                error=str(exc),
            )


_ai_gateway: AIGateway | None = None


def get_ai_gateway() -> AIGateway:
    """返回延迟初始化的 AI 网关单例。"""
    global _ai_gateway
    if _ai_gateway is None:
        _ai_gateway = AIGateway(settings)
    return _ai_gateway
