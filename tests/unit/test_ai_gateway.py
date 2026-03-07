"""统一 AI 网关测试。"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.gateway import AIGateway, AIRequest


def _make_settings(provider: str = "codex", enabled: bool = True) -> MagicMock:
    settings = MagicMock()
    settings.ai_provider = provider
    settings.codex_api_key = "codex-key" if enabled and provider == "codex" else ""
    settings.codex_base_url = "https://example.com"
    settings.codex_model_id = "gpt-test"
    settings.codex_timeout = 30
    settings.codex_max_retries = 2
    settings.codex_thinking_default = "medium"
    settings.codex_max_tokens = 4096
    return settings


class TestAIGateway:
    @pytest.mark.asyncio
    @patch("app.ai.gateway.CodexClient")
    async def test_execute_json_with_system_prompt(self, mock_client_cls: MagicMock):
        """JSON 请求应拼接 system prompt 并返回结果。"""
        mock_client = MagicMock()
        mock_client.chat_json = AsyncMock(return_value={"ok": True})
        mock_client.get_last_usage.return_value = {"total_tokens": 12}
        mock_client_cls.return_value = mock_client

        gateway = AIGateway(_make_settings("codex", enabled=True))
        result = await gateway.execute(
            AIRequest(
                prompt="请输出 JSON",
                system_prompt="你是分析助手",
                response_format="json",
                task_name="unit_test",
            )
        )

        assert result.ok is True
        assert result.content == {"ok": True}
        assert result.token_usage == {"total_tokens": 12}
        called_prompt = mock_client.chat_json.await_args.args[0]
        assert "你是分析助手" in called_prompt
        assert "请输出 JSON" in called_prompt

    @pytest.mark.asyncio
    async def test_execute_disabled_returns_error(self):
        """未启用时应返回统一错误。"""
        gateway = AIGateway(_make_settings("codex", enabled=False))
        result = await gateway.execute(AIRequest(prompt="hello"))

        assert result.ok is False
        assert result.error == "ai_disabled"

    @pytest.mark.asyncio
    async def test_execute_unknown_provider_returns_error(self):
        """非 codex provider 应被禁用。"""
        gateway = AIGateway(_make_settings("gemini", enabled=True))
        result = await gateway.execute(AIRequest(prompt="hello"))

        assert result.ok is False
        assert result.error == "ai_disabled"
