"""Codex API 客户端。

封装 OpenAI 兼容 API，提供异步聊天调用、JSON 解析、超时和重试。
支持自定义 base_url 和 thinking 参数。
"""

import asyncio
import json
import logging
from typing import Any

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 自定义异常
# ---------------------------------------------------------------------------


class CodexError(Exception):
    """Codex 客户端基础异常。"""


class CodexTimeoutError(CodexError):
    """请求超时。"""


class CodexAPIError(CodexError):
    """API 级别错误（限流、认证、服务端错误）。"""


class CodexResponseParseError(CodexError):
    """响应 JSON 解析失败。"""

    def __init__(self, message: str, raw_response: str = "") -> None:
        super().__init__(message)
        self.raw_response = raw_response


# ---------------------------------------------------------------------------
# CodexClient
# ---------------------------------------------------------------------------


class CodexClient:
    """Codex 异步客户端（OpenAI 兼容 API）。

    Args:
        api_key: API 密钥
        base_url: API 基础 URL
        model_id: 模型标识符
        timeout: 请求超时秒数
        max_retries: 瞬态错误重试次数
        thinking_default: 思考模式（xhigh/high/medium/low）
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://gmn.chuangzuoli.com/v1",
        model_id: str = "gpt-5.3-codex",
        timeout: int = 30,
        max_retries: int = 2,
        thinking_default: str = "xhigh",
    ) -> None:
        self._model_id = model_id
        self._timeout = timeout
        self._max_retries = max_retries
        self._thinking_default = thinking_default
        self._last_usage: dict[str, int] = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )

    async def chat(self, prompt: str, max_tokens: int = 2000, response_format: str = "text") -> str:
        """调用 Codex API，返回文本响应。

        Args:
            prompt: 输入提示词
            max_tokens: 最大输出 token 数
            response_format: 响应格式（text/json_object）

        Returns:
            模型响应文本

        Raises:
            CodexTimeoutError: 请求超时
            CodexAPIError: API 错误（重试耗尽后）
        """
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                kwargs = {
                    "model": self._model_id,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "extra_body": {"thinkingDefault": self._thinking_default},
                }

                # 如果需要 JSON 格式，添加 response_format
                if response_format == "json_object":
                    kwargs["response_format"] = {"type": "json_object"}

                response = await asyncio.wait_for(
                    self._client.chat.completions.create(**kwargs),
                    timeout=self._timeout,
                )

                # 更新 token 用量
                if response.usage:
                    self._last_usage = {
                        "prompt_tokens": response.usage.prompt_tokens or 0,
                        "completion_tokens": response.usage.completion_tokens or 0,
                        "total_tokens": response.usage.total_tokens or 0,
                    }

                return response.choices[0].message.content or ""

            except asyncio.TimeoutError:
                raise CodexTimeoutError(
                    f"Codex API 请求超时（{self._timeout}s）"
                )
            except CodexTimeoutError:
                raise
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Codex API 调用失败（第 %d 次）：%s (类型: %s)",
                    attempt + 1, str(exc), type(exc).__name__,
                )
                if attempt < self._max_retries:
                    wait = 2 ** attempt  # 指数退避：1s, 2s, ...
                    logger.warning("等待 %ds 后重试", wait)
                    await asyncio.sleep(wait)

        raise CodexAPIError(f"Codex API 调用失败（已重试 {self._max_retries} 次）：{last_error}")

    async def chat_json(self, prompt: str, max_tokens: int = 2000) -> dict[str, Any]:
        """调用 Codex API 并解析 JSON 响应。

        Args:
            prompt: 输入提示词
            max_tokens: 最大输出 token 数

        Returns:
            解析后的 dict

        Raises:
            CodexResponseParseError: JSON 解析失败
            CodexTimeoutError: 请求超时
            CodexAPIError: API 错误
        """
        text = await self.chat(prompt, max_tokens, response_format="json_object")
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError) as exc:
            raise CodexResponseParseError(
                f"Codex 响应 JSON 解析失败：{exc}",
                raw_response=text,
            )

    def get_last_usage(self) -> dict[str, int]:
        """返回最近一次 API 调用的 token 用量。"""
        return self._last_usage.copy()
