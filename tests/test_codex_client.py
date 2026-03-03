"""测试 Codex API 客户端。"""

import asyncio
import os

import pytest

from app.ai.clients.codex import CodexClient, CodexError


@pytest.mark.asyncio
async def test_codex_chat_json():
    """测试 Codex JSON 响应解析。"""
    api_key = os.getenv("CODEX_API_KEY", "")
    if not api_key:
        pytest.skip("CODEX_API_KEY 未配置")

    client = CodexClient(
        api_key=api_key,
        base_url="https://gmn.chuangzuoli.com/v1",
        model_id="gpt-5.3-codex",
        thinking_default="xhigh",
        timeout=60,
    )

    prompt = """请分析以下股票并返回 JSON 格式：
{
  "analysis": [
    {
      "ts_code": "600519.SH",
      "score": 85,
      "signal": "BUY",
      "reasoning": "贵州茅台基本面优秀，长期持有价值高"
    }
  ]
}

只返回 JSON，不要其他文字。"""

    response = await client.chat_json(prompt, max_tokens=500)

    print(f"\n[Codex JSON 响应]\n{response}")
    print(f"\n[Token 用量] {client.get_last_usage()}")

    assert isinstance(response, dict)
    assert "analysis" in response
    assert isinstance(response["analysis"], list)
    assert len(response["analysis"]) > 0
    assert "ts_code" in response["analysis"][0]
    assert "score" in response["analysis"][0]
    assert "signal" in response["analysis"][0]
    assert "reasoning" in response["analysis"][0]


if __name__ == "__main__":
    # 直接运行测试
    asyncio.run(test_codex_chat_json())

