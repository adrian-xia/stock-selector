"""Gemini Flash API 客户端。

封装 google-genai SDK，提供异步聊天调用、JSON 解析、超时和重试。
"""

import asyncio
import json
import logging
from typing import Any

from google import genai
from google.genai.types import GenerateContentConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 自定义异常
# ---------------------------------------------------------------------------


class GeminiError(Exception):
    """Gemini 客户端基础异常。"""


class GeminiTimeoutError(GeminiError):
    """请求超时。"""


class GeminiAPIError(GeminiError):
    """API 级别错误（限流、认证、服务端错误）。"""


class GeminiResponseParseError(GeminiError):
    """响应 JSON 解析失败。"""

    def __init__(self, message: str, raw_response: str = "") -> None:
        super().__init__(message)
        self.raw_response = raw_response


# ---------------------------------------------------------------------------
# GeminiClient
# ---------------------------------------------------------------------------


class GeminiClient:
    """Gemini Flash 异步客户端。

    Args:
        api_key: Gemini API 密钥
        model_id: 模型标识符，默认 gemini-2.0-flash
        timeout: 请求超时秒数
        max_retries: 瞬态错误重试次数
    """

    def __init__(
        self,
        api_key: str,
        model_id: str = "gemini-2.0-flash",
        timeout: int = 30,
        max_retries: int = 2,
    ) -> None:
        if not api_key:
            raise ValueError("Gemini API key 不能为空")
        self._model_id = model_id
        self._timeout = timeout
        self._max_retries = max_retries
        self._client = genai.Client(api_key=api_key)
        self._last_usage: dict[str, int] = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

    async def chat(self, prompt: str, max_tokens: int = 2000) -> str:
        """调用 Gemini API，返回文本响应。

        Args:
            prompt: 输入提示词
            max_tokens: 最大输出 token 数

        Returns:
            模型响应文本

        Raises:
            GeminiTimeoutError: 请求超时
            GeminiAPIError: API 错误（重试耗尽后）
        """
        config = GenerateContentConfig(
            response_mime_type="application/json",
            max_output_tokens=max_tokens,
        )

        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = await asyncio.wait_for(
                    self._client.aio.models.generate_content(
                        model=self._model_id,
                        contents=prompt,
                        config=config,
                    ),
                    timeout=self._timeout,
                )
                # 更新 token 用量
                if response.usage_metadata:
                    self._last_usage = {
                        "prompt_tokens": response.usage_metadata.prompt_token_count or 0,
                        "completion_tokens": response.usage_metadata.candidates_token_count or 0,
                        "total_tokens": response.usage_metadata.total_token_count or 0,
                    }
                return response.text or ""

            except asyncio.TimeoutError:
                raise GeminiTimeoutError(
                    f"Gemini API 请求超时（{self._timeout}s）"
                )
            except GeminiTimeoutError:
                raise
            except Exception as exc:
                last_error = exc
                if attempt < self._max_retries:
                    wait = 2 ** attempt  # 指数退避：1s, 2s, ...
                    logger.warning(
                        "Gemini API 调用失败（第 %d 次），%ds 后重试：%s",
                        attempt + 1, wait, exc,
                    )
                    await asyncio.sleep(wait)

        raise GeminiAPIError(f"Gemini API 调用失败（已重试 {self._max_retries} 次）：{last_error}")

    async def chat_json(self, prompt: str, max_tokens: int = 2000) -> dict[str, Any]:
        """调用 Gemini API 并解析 JSON 响应。

        Args:
            prompt: 输入提示词
            max_tokens: 最大输出 token 数

        Returns:
            解析后的 dict

        Raises:
            GeminiResponseParseError: JSON 解析失败
            GeminiTimeoutError: 请求超时
            GeminiAPIError: API 错误
        """
        text = await self.chat(prompt, max_tokens)
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError) as exc:
            raise GeminiResponseParseError(
                f"Gemini 响应 JSON 解析失败：{exc}",
                raw_response=text,
            )

    def get_last_usage(self) -> dict[str, int]:
        """返回最近一次 API 调用的 token 用量。"""
        return self._last_usage.copy()
