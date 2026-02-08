"""GeminiClient 单元测试。"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.clients.gemini import (
    GeminiAPIError,
    GeminiClient,
    GeminiError,
    GeminiResponseParseError,
    GeminiTimeoutError,
)


class TestGeminiClientInit:
    """构造函数测试。"""

    def test_empty_api_key_raises(self) -> None:
        with pytest.raises(ValueError, match="GEMINI_API_KEY"):
            GeminiClient(api_key="")

    @patch("app.ai.clients.gemini.genai.Client")
    def test_valid_init(self, mock_client_cls: MagicMock) -> None:
        client = GeminiClient(api_key="test-key", model_id="gemini-2.0-flash")
        mock_client_cls.assert_called_once_with(api_key="test-key")
        assert client._model_id == "gemini-2.0-flash"

    @patch("app.ai.clients.gemini.genai.Client")
    def test_default_usage(self, mock_client_cls: MagicMock) -> None:
        client = GeminiClient(api_key="test-key")
        usage = client.get_last_usage()
        assert usage == {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


class TestGeminiClientChat:
    """chat() 方法测试。"""

    @patch("app.ai.clients.gemini.genai.Client")
    async def test_successful_chat(self, mock_client_cls: MagicMock) -> None:
        # 构造 mock 响应
        mock_response = MagicMock()
        mock_response.text = '{"result": "ok"}'
        mock_response.usage_metadata.prompt_token_count = 10
        mock_response.usage_metadata.candidates_token_count = 20
        mock_response.usage_metadata.total_token_count = 30

        mock_aio = MagicMock()
        mock_aio.models.generate_content = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.aio = mock_aio

        client = GeminiClient(api_key="test-key")
        result = await client.chat("test prompt")

        assert result == '{"result": "ok"}'
        assert client.get_last_usage() == {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        }

    @patch("app.ai.clients.gemini.genai.Client")
    async def test_timeout_raises(self, mock_client_cls: MagicMock) -> None:
        mock_aio = MagicMock()
        mock_aio.models.generate_content = AsyncMock(side_effect=asyncio.TimeoutError)
        mock_client_cls.return_value.aio = mock_aio

        client = GeminiClient(api_key="test-key", timeout=1)
        with pytest.raises(GeminiTimeoutError):
            await client.chat("test")

    @patch("app.ai.clients.gemini.genai.Client")
    async def test_api_error_retries_then_raises(self, mock_client_cls: MagicMock) -> None:
        mock_aio = MagicMock()
        mock_aio.models.generate_content = AsyncMock(
            side_effect=RuntimeError("rate limited")
        )
        mock_client_cls.return_value.aio = mock_aio

        client = GeminiClient(api_key="test-key", max_retries=1)
        with pytest.raises(GeminiAPIError, match="rate limited"):
            await client.chat("test")

        # 应该调用了 2 次（1 次初始 + 1 次重试）
        assert mock_aio.models.generate_content.call_count == 2

    @patch("app.ai.clients.gemini.genai.Client")
    async def test_timeout_is_gemini_error(self, mock_client_cls: MagicMock) -> None:
        """GeminiTimeoutError 应该是 GeminiError 的子类。"""
        mock_aio = MagicMock()
        mock_aio.models.generate_content = AsyncMock(side_effect=asyncio.TimeoutError)
        mock_client_cls.return_value.aio = mock_aio

        client = GeminiClient(api_key="test-key", timeout=1)
        with pytest.raises(GeminiError):
            await client.chat("test")


class TestGeminiClientChatJson:
    """chat_json() 方法测试。"""

    @patch("app.ai.clients.gemini.genai.Client")
    async def test_valid_json(self, mock_client_cls: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.text = '{"analysis": []}'
        mock_response.usage_metadata.prompt_token_count = 5
        mock_response.usage_metadata.candidates_token_count = 10
        mock_response.usage_metadata.total_token_count = 15

        mock_aio = MagicMock()
        mock_aio.models.generate_content = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.aio = mock_aio

        client = GeminiClient(api_key="test-key")
        result = await client.chat_json("test")
        assert result == {"analysis": []}

    @patch("app.ai.clients.gemini.genai.Client")
    async def test_invalid_json_raises(self, mock_client_cls: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.text = "not json at all"
        mock_response.usage_metadata.prompt_token_count = 5
        mock_response.usage_metadata.candidates_token_count = 10
        mock_response.usage_metadata.total_token_count = 15

        mock_aio = MagicMock()
        mock_aio.models.generate_content = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.aio = mock_aio

        client = GeminiClient(api_key="test-key")
        with pytest.raises(GeminiResponseParseError) as exc_info:
            await client.chat_json("test")
        assert exc_info.value.raw_response == "not json at all"
