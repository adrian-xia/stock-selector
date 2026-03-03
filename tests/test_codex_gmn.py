"""测试 Codex 客户端（gmn.chuangzuoli.com 专有协议）。"""

import asyncio
import os

from app.ai.clients.codex import CodexClient


async def test_codex_chat():
    """测试 Codex 聊天功能。"""
    api_key = os.environ.get("CODEX_API_KEY", "")
    if not api_key:
        print("❌ 未设置 CODEX_API_KEY 环境变量")
        return

    client = CodexClient(
        api_key=api_key,
        base_url="https://gmn.chuangzuoli.com",
        model_id="gpt-5.3-codex",
        thinking_default="xhigh",
        timeout=30,
    )

    try:
        print("🚀 测试 Codex API 调用...")
        print(f"📍 Base URL: https://gmn.chuangzuoli.com")
        print(f"🤖 Model: gpt-5.3-codex")
        print(f"🧠 Thinking: xhigh")
        print()

        # 测试简单对话
        prompt = "你好，请用一句话介绍你自己。"
        print(f"💬 Prompt: {prompt}")
        print()

        response = await client.chat(prompt, max_tokens=200)
        print(f"✅ Response: {response}")
        print()

        # 显示 token 用量
        usage = client.get_last_usage()
        print(f"📊 Token 用量: {usage}")
        print()

        # 测试 JSON 模式
        print("🧪 测试 JSON 模式...")
        json_prompt = '请返回一个 JSON 对象，包含字段 "name": "Codex", "version": "5.3"'
        json_response = await client.chat_json(json_prompt, max_tokens=200)
        print(f"✅ JSON Response: {json_response}")
        print()

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_codex_chat())
