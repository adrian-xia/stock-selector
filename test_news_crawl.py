"""淘股吧：带 session cookie 调 API + 雪球最终方案确认。"""
import asyncio
import json
import re
import traceback

import httpx

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://www.tgb.cn/quotes/600519",
}


async def test_taoguba_with_session():
    """淘股吧：先访问页面拿 cookie，再调 API"""
    print("=== 淘股吧带 session 测试 ===\n")

    async with httpx.AsyncClient(
        timeout=15, headers=HEADERS, follow_redirects=True
    ) as client:
        # 1. 先访问首页和个股页面，积累 cookie
        await client.get("https://www.tgb.cn/")
        await client.get("https://www.tgb.cn/quotes/600519")
        cookies = dict(client.cookies)
        print(f"  cookies: {cookies}\n")

        # 2. 用 session cookie 调 API
        apis = [
            ("getStockUpToDate", "https://www.tgb.cn/quotes/getStockUpToDate",
             {"code": "600519", "page": "1"}),
            ("getStockHeat", "https://www.tgb.cn/quotes/getStockHeat",
             {"code": "600519", "page": "1"}),
            ("getStockRearch", "https://www.tgb.cn/quotes/getStockRearch",
             {"code": "600519", "page": "1"}),
            ("getStockUpToDate stockCode", "https://www.tgb.cn/quotes/getStockUpToDate",
             {"stockCode": "600519", "page": "1"}),
            ("getStockUpToDate stockCode sh", "https://www.tgb.cn/quotes/getStockUpToDate",
             {"stockCode": "sh600519", "page": "1"}),
        ]

        for name, url, params in apis:
            try:
                resp = await client.get(url, params=params)
                data = resp.json()
                status = data.get("status")
                err = data.get("errorMessage", "")
                if status is True:
                    print(f"  {name}: [SUCCESS]")
                    print(f"    {json.dumps(data, ensure_ascii=False)[:400]}")
                else:
                    print(f"  {name}: err={err} (code={data.get('errorCode')})")
            except Exception as e:
                print(f"  {name}: {e}")
            await asyncio.sleep(0.3)

        # 3. 尝试 POST
        print("\n  --- POST 测试 ---")
        for name, url, body in [
            ("POST getStockUpToDate", "https://www.tgb.cn/quotes/getStockUpToDate",
             {"code": "600519", "page": 1}),
            ("POST getStockHeat", "https://www.tgb.cn/quotes/getStockHeat",
             {"code": "600519", "page": 1}),
        ]:
            try:
                resp = await client.post(url, data=body)
                data = resp.json()
                status = data.get("status")
                err = data.get("errorMessage", "")
                if status is True:
                    print(f"  {name}: [SUCCESS]")
                    print(f"    {json.dumps(data, ensure_ascii=False)[:400]}")
                else:
                    print(f"  {name}: err={err}")
            except Exception as e:
                print(f"  {name}: {e}")
            await asyncio.sleep(0.3)

        # 4. 直接解析个股页面中已有的帖子链接作为 fallback
        print("\n  --- 页面内帖子链接提取 ---")
        resp = await client.get("https://www.tgb.cn/quotes/600519")
        html = resp.text
        # /a/xxx 格式的帖子链接
        posts = re.findall(r'<a[^>]*href="(https://www\.tgb\.cn/a/[^"]+)"[^>]*>([^<]*《[^<]*》[^<]*)</a>', html)
        if not posts:
            posts = re.findall(r'href="((?:https://www\.tgb\.cn)?/a/[^"]+)"[^>]*>([^<]{4,})</a>', html)
        print(f"  帖子链接: {len(posts)} 个")
        for href, title in posts[:10]:
            print(f"    {title.strip()[:60]} -> {href}")

        # 5. 尝试新浪财经作为替代方案
        print("\n\n=== 新浪财经 API 测试（替代方案）===\n")
        sina_apis = [
            ("个股新闻", "https://feed.mix.sina.com.cn/api/roll/get",
             {"pageid": "155", "lid": "2516", "k": "600519", "num": "10", "page": "1"}),
            ("股票新闻v2", "https://finance.sina.com.cn/realstock/company/sh600519/nc.shtml", {}),
            ("7x24快讯", "https://zhibo.sina.com.cn/api/zhibo/feed",
             {"page": "1", "page_size": "10", "zhibo_id": "152", "tag_id": "0", "type": "0"}),
        ]
        for name, url, params in sina_apis:
            try:
                resp = await client.get(url, params=params)
                ct = resp.headers.get("content-type", "")
                text = resp.text.strip()
                is_json = "json" in ct or text[:1] in ("{", "[")
                if is_json:
                    data = resp.json()
                    print(f"  {name}: {resp.status_code} [JSON]")
                    print(f"    {json.dumps(data, ensure_ascii=False)[:300]}")
                else:
                    # 看看是不是 HTML 页面有新闻
                    news_count = text.count("新闻") + text.count("公告")
                    print(f"  {name}: {resp.status_code} ct={ct[:30]} len={len(text)} 新闻关键词={news_count}")
            except Exception as e:
                print(f"  {name}: {e}")
            await asyncio.sleep(0.3)

        # 6. 同花顺新闻 API
        print("\n=== 同花顺新闻 API 测试 ===\n")
        ths_apis = [
            ("个股新闻", "https://basic.10jqka.com.cn/ajax/stock/newsList/600519",
             {}),
            ("个股公告", "https://basic.10jqka.com.cn/ajax/stock/notice/600519",
             {}),
            ("个股资讯", "https://news.10jqka.com.cn/tapp/news/push/stock",
             {"page": "1", "tag": "", "track": "stock", "stockcode": "600519"}),
        ]
        for name, url, params in ths_apis:
            try:
                resp = await client.get(url, params=params)
                ct = resp.headers.get("content-type", "")
                text = resp.text.strip()
                is_json = "json" in ct or text[:1] in ("{", "[")
                if is_json:
                    data = resp.json()
                    print(f"  {name}: {resp.status_code} [JSON]")
                    print(f"    {json.dumps(data, ensure_ascii=False)[:300]}")
                elif len(text) > 100:
                    print(f"  {name}: {resp.status_code} ct={ct[:30]} len={len(text)}")
                    # 提取标题
                    titles = re.findall(r'<a[^>]*>([^<]{10,})</a>', text)
                    if titles:
                        print(f"    标题示例: {titles[0][:60]}")
                else:
                    print(f"  {name}: {resp.status_code} ct={ct[:30]} 前100: {text[:100]}")
            except Exception as e:
                print(f"  {name}: {e}")
            await asyncio.sleep(0.3)


async def main():
    try:
        await test_taoguba_with_session()
    except Exception:
        traceback.print_exc()


asyncio.run(main())
