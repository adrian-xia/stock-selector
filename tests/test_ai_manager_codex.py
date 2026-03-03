"""测试 AIManager 的 Codex 提供商集成。"""

import asyncio
import os

from app.ai.manager import AIManager
from app.config import Settings


async def test_ai_manager_codex():
    """测试 AIManager 使用 Codex 提供商。"""
    api_key = os.environ.get("CODEX_API_KEY", "")
    if not api_key:
        print("❌ 未设置 CODEX_API_KEY 环境变量")
        return

    # 创建配置，使用 Codex 提供商
    settings = Settings(
        ai_provider="codex",
        codex_api_key=api_key,
        codex_base_url="https://gmn.chuangzuoli.com",
        codex_model_id="gpt-5.3-codex",
        codex_thinking_default="xhigh",
        ai_daily_call_limit=0,  # 不限制
    )

    manager = AIManager(settings)

    print("🚀 测试 AIManager + Codex 提供商")
    print(f"📍 Provider: {settings.ai_provider}")
    print(f"🤖 Model: {settings.codex_model_id}")
    print(f"✅ AI Enabled: {manager.is_enabled}")
    print()

    if not manager.is_enabled:
        print("❌ AI Manager 未启用")
        return

    try:
        # 直接测试底层客户端
        client = manager._get_client()

        prompt = "请用一句话介绍 A 股市场的特点。"
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
        json_prompt = '请返回一个 JSON 对象，包含字段 "market": "A股", "feature": "特点描述"'
        json_response = await client.chat_json(json_prompt, max_tokens=200)
        print(f"✅ JSON Response: {json_response}")
        print()

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 关闭客户端连接
        if hasattr(client, 'close'):
            await client.close()


if __name__ == "__main__":
    asyncio.run(test_ai_manager_codex())
