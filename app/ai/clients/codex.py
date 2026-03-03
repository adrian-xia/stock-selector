"""Codex API 客户端。

封装 gmn.chuangzuoli.com 专有协议，提供异步聊天调用、JSON 解析、超时和重试。
使用 /v1/responses 端点和 input 数组格式。
"""

import asyncio
import json
import logging
from typing import Any

import httpx

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
    """Codex 异步客户端（gmn.chuangzuoli.com 专有协议）。

    Args:
        api_key: API 密钥
        base_url: API 基础 URL（默认 https://gmn.chuangzuoli.com）
        model_id: 模型标识符（如 gpt-5.3-codex）
        timeout: 请求超时秒数
        max_retries: 瞬态错误重试次数
        thinking_default: 思考模式（xhigh/high/medium/low）
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://gmn.chuangzuoli.com",
        model_id: str = "gpt-5.3-codex",
        timeout: int = 30,
        max_retries: int = 2,
        thinking_default: str = "xhigh",
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model_id = model_id
        self._timeout = timeout
        self._max_retries = max_retries
        self._thinking_default = thinking_default
        self._last_usage: dict[str, int] = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
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
                # 构造专有协议请求体
                payload = {
                    "model": self._model_id,
                    "input": [
                        {
                            "type": "message",
                            "role": "user",
                            "content": [
                                {
                                    "type": "input_text",
                                    "text": prompt,
                                }
                            ],
                        }
                    ],
                }

                # 如果需要 JSON 格式，添加到 payload
                if response_format == "json_object":
                    payload["text"] = {"format": {"type": "json_object"}}

                # 发送请求到 /v1/responses 端点
                url = f"{self._base_url}/v1/responses"
                response = await self._client.post(url, json=payload)
                response.raise_for_status()

                # 解析响应
                data = response.json()

                # 更新 token 用量
                if "usage" in data:
                    usage = data["usage"]
                    self._last_usage = {
                        "prompt_tokens": usage.get("input_tokens", 0),
                        "completion_tokens": usage.get("output_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                    }

                # 提取响应文本
                # 响应格式：{"output": [{"type": "message", "content": [{"type": "output_text", "text": "..."}]}]}
                if "output" in data and len(data["output"]) > 0:
                    output = data["output"][0]
                    if "content" in output and len(output["content"]) > 0:
                        content = output["content"][0]
                        if content.get("type") == "output_text":
                            return content.get("text", "")

                # 如果格式不符合预期，返回原始 JSON
                logger.warning("Codex 响应格式未知，返回原始 JSON: %s", data)
                return json.dumps(data, ensure_ascii=False)

            except httpx.TimeoutException:
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

    async def close(self) -> None:
        """关闭 HTTP 客户端连接。"""
        await self._client.aclose()
