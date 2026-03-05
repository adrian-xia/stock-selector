"""StarMap Phase 0: 新闻源 PoC 验证脚本。

评估三个候选宏观新闻数据源的可用性：
1. Tushare news / major_news 接口
2. 新浪 7x24 快讯（已有 SinaCrawler，评估宏观级覆盖）
3. 财联社电报 API

评估维度：
- 数据可达性：能否成功获取数据
- 覆盖度：交易日新闻条数
- 字段质量：标题、正文、时间戳、来源完整性
- 延迟：接口响应时间
- 宏观相关性：新闻中宏观/行业信息的占比

Usage:
    uv run python -m app.research.news.sources_poc
"""

import asyncio
import json
import logging
import re
import time
from datetime import date, datetime

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# HTML 清理
_HTML_RE = re.compile(r"<[^>]+>")

# 宏观关键词（用于评估新闻的宏观相关性）
_MACRO_KEYWORDS = [
    "央行", "降准", "降息", "LPR", "MLF", "逆回购", "国务院",
    "GDP", "CPI", "PPI", "PMI", "社融", "M2", "外汇", "美联储",
    "利率", "通胀", "就业", "失业率", "财政", "货币政策",
    "A股", "沪指", "深成指", "创业板", "北向", "外资",
    "行业", "板块", "新能源", "半导体", "AI", "人工智能",
    "医药", "消费", "地产", "房地产", "银行", "券商",
    "涨停", "跌停", "大盘", "市场", "风险", "利好", "利空",
]


def _count_macro_hits(text: str) -> int:
    """统计文本中命中的宏观关键词数量。"""
    return sum(1 for kw in _MACRO_KEYWORDS if kw in text)


def _assess_fields(item: dict, required: list[str]) -> dict:
    """评估字段完整性。"""
    present = [f for f in required if item.get(f)]
    missing = [f for f in required if not item.get(f)]
    return {"present": present, "missing": missing, "completeness": len(present) / len(required)}


# ---------------------------------------------------------------------------
# 数据源 1: Tushare news / major_news
# ---------------------------------------------------------------------------

async def test_tushare_news() -> dict:
    """测试 Tushare 新闻接口。"""
    result = {
        "source": "tushare",
        "reachable": False,
        "news_count": 0,
        "major_news_count": 0,
        "latency_ms": 0,
        "macro_ratio": 0.0,
        "field_quality": {},
        "sample_titles": [],
        "error": None,
        "notes": [],
    }

    try:
        from app.config import settings
        import tushare as ts

        pro = ts.pro_api(settings.tushare_token)
        today_str = date.today().strftime("%Y%m%d")

        # 测试 major_news（重大新闻）
        start = time.monotonic()
        try:
            df_major = pro.major_news(
                start_date=today_str,
                end_date=today_str,
                fields="title,content,pub_time,src",
            )
            latency = (time.monotonic() - start) * 1000
            result["latency_ms"] = round(latency)

            if df_major is not None and len(df_major) > 0:
                result["reachable"] = True
                result["major_news_count"] = len(df_major)

                # 采样分析
                for _, row in df_major.head(10).iterrows():
                    title = str(row.get("title", ""))
                    result["sample_titles"].append(title[:80])
                    content = str(row.get("content", ""))
                    if _count_macro_hits(title + content) > 0:
                        result["macro_ratio"] += 1

                if result["major_news_count"] > 0:
                    result["macro_ratio"] = round(
                        result["macro_ratio"] / min(result["major_news_count"], 10), 2
                    )

                # 字段质量
                sample = df_major.iloc[0].to_dict()
                result["field_quality"] = _assess_fields(
                    sample, ["title", "content", "pub_time", "src"]
                )
            else:
                result["notes"].append("major_news 返回空 DataFrame")
        except Exception as e:
            err_str = str(e)
            if "权限" in err_str or "积分" in err_str or "permission" in err_str.lower():
                result["notes"].append(f"major_news 需要更高权限: {err_str[:100]}")
            else:
                result["error"] = f"major_news 失败: {err_str[:200]}"

        # 测试 news（新闻快讯）
        start2 = time.monotonic()
        try:
            df_news = pro.news(
                start_date=today_str,
                end_date=today_str,
                src="sina",
                fields="title,content,pub_time,channels",
            )
            latency2 = (time.monotonic() - start2) * 1000

            if df_news is not None and len(df_news) > 0:
                result["reachable"] = True
                result["news_count"] = len(df_news)
                if not result["latency_ms"]:
                    result["latency_ms"] = round(latency2)
                result["notes"].append(f"news 接口返回 {len(df_news)} 条")
            else:
                result["notes"].append("news 返回空 DataFrame")
        except Exception as e:
            err_str = str(e)
            if "权限" in err_str or "积分" in err_str:
                result["notes"].append(f"news 需要更高权限: {err_str[:100]}")
            else:
                result["notes"].append(f"news 失败: {err_str[:100]}")

    except ImportError:
        result["error"] = "tushare 未安装或 settings 加载失败"
    except Exception as e:
        result["error"] = str(e)[:200]

    return result


# ---------------------------------------------------------------------------
# 数据源 2: 新浪 7x24 快讯
# ---------------------------------------------------------------------------

async def test_sina_7x24() -> dict:
    """测试新浪 7x24 快讯（宏观新闻覆盖度评估）。"""
    result = {
        "source": "sina_7x24",
        "reachable": False,
        "news_count": 0,
        "latency_ms": 0,
        "macro_ratio": 0.0,
        "field_quality": {},
        "sample_titles": [],
        "error": None,
        "notes": [],
    }

    url = "https://zhibo.sina.com.cn/api/zhibo/feed"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Referer": "https://finance.sina.com.cn/",
    }

    try:
        async with httpx.AsyncClient(timeout=15, headers=headers) as client:
            # 拉取 3 页（约 60 条）
            all_items = []
            total_latency = 0

            for page in range(1, 4):
                start = time.monotonic()
                resp = await client.get(url, params={
                    "page": str(page),
                    "page_size": "20",
                    "zhibo_id": "152",
                })
                total_latency += (time.monotonic() - start) * 1000
                resp.raise_for_status()
                data = resp.json()
                items = data.get("result", {}).get("data", {}).get("feed", {}).get("list", [])
                all_items.extend(items)

                if not items:
                    break
                await asyncio.sleep(0.5)

            result["reachable"] = True
            result["news_count"] = len(all_items)
            result["latency_ms"] = round(total_latency / 3)

            # 评估宏观覆盖
            macro_count = 0
            for item in all_items[:30]:
                text = _HTML_RE.sub("", item.get("rich_text", ""))
                if not text.strip():
                    continue

                if _count_macro_hits(text) >= 1:
                    macro_count += 1
                if len(result["sample_titles"]) < 10:
                    result["sample_titles"].append(text.strip()[:80])

            sampled = min(len(all_items), 30)
            result["macro_ratio"] = round(macro_count / sampled, 2) if sampled > 0 else 0

            # 字段质量
            if all_items:
                sample = all_items[0]
                quality_fields = {
                    "rich_text": sample.get("rich_text", ""),
                    "create_time": sample.get("create_time", ""),
                    "type": sample.get("type", ""),
                    "tag": json.dumps(sample.get("tag", []), ensure_ascii=False),
                }
                result["field_quality"] = _assess_fields(
                    quality_fields, ["rich_text", "create_time", "type", "tag"]
                )

            result["notes"].append(
                f"宏观相关新闻占比: {macro_count}/{sampled} = {result['macro_ratio']:.0%}"
            )

    except Exception as e:
        result["error"] = str(e)[:200]

    return result


# ---------------------------------------------------------------------------
# 数据源 3: 财联社电报
# ---------------------------------------------------------------------------

async def test_cls_telegraph() -> dict:
    """测试财联社电报 API。"""
    result = {
        "source": "cls_telegraph",
        "reachable": False,
        "news_count": 0,
        "latency_ms": 0,
        "macro_ratio": 0.0,
        "field_quality": {},
        "sample_titles": [],
        "error": None,
        "notes": [],
    }

    # 财联社电报公开 API
    url = "https://www.cls.cn/nodeapi/updateTelegraph"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Referer": "https://www.cls.cn/telegraph",
    }

    try:
        async with httpx.AsyncClient(timeout=15, headers=headers) as client:
            start = time.monotonic()
            resp = await client.get(url, params={"rn": "30", "os": "web", "sv": "8.4.6"})
            latency = (time.monotonic() - start) * 1000
            result["latency_ms"] = round(latency)

            if resp.status_code == 200:
                data = resp.json()
                telegraphs = data.get("data", {}).get("roll_data", [])
                result["reachable"] = True
                result["news_count"] = len(telegraphs)

                # 评估
                macro_count = 0
                for item in telegraphs[:30]:
                    title = _HTML_RE.sub("", item.get("title", "") or item.get("content", ""))
                    if _count_macro_hits(title) >= 1:
                        macro_count += 1
                    if len(result["sample_titles"]) < 10:
                        result["sample_titles"].append(title.strip()[:80])

                sampled = min(len(telegraphs), 30)
                result["macro_ratio"] = round(macro_count / sampled, 2) if sampled > 0 else 0

                # 字段质量
                if telegraphs:
                    sample = telegraphs[0]
                    result["field_quality"] = _assess_fields(
                        sample, ["title", "content", "ctime", "source"]
                    )

                result["notes"].append(
                    f"宏观相关占比: {macro_count}/{sampled} = {result['macro_ratio']:.0%}"
                )
            else:
                result["notes"].append(f"HTTP {resp.status_code}")

    except Exception as e:
        result["error"] = str(e)[:200]

    return result


# ---------------------------------------------------------------------------
# 汇总评估
# ---------------------------------------------------------------------------

def generate_poc_verdict(results: list[dict]) -> dict:
    """生成 PoC 综合评估结论。"""
    verdict = {
        "timestamp": datetime.now().isoformat(),
        "sources_tested": len(results),
        "recommended_primary": None,
        "recommended_fallback": None,
        "starmap_scope": "full",  # full / reduced / minimal
        "details": [],
    }

    # 按可达性 + 宏观覆盖率排序
    reachable = [r for r in results if r["reachable"]]

    if not reachable:
        verdict["starmap_scope"] = "minimal"
        verdict["details"].append("所有新闻源均不可达，StarMap 仅启用纯量化模式")
        return verdict

    # 按宏观覆盖率排序
    reachable.sort(key=lambda x: x["macro_ratio"], reverse=True)

    best = reachable[0]
    verdict["recommended_primary"] = best["source"]

    if len(reachable) > 1:
        verdict["recommended_fallback"] = reachable[1]["source"]

    # 判断 scope
    if best["macro_ratio"] >= 0.3 and best["news_count"] >= 10:
        verdict["starmap_scope"] = "full"
        verdict["details"].append(
            f"推荐主数据源 {best['source']}，宏观覆盖率 {best['macro_ratio']:.0%}，"
            f"条数 {best['news_count']}，延迟 {best['latency_ms']}ms"
        )
    elif best["macro_ratio"] >= 0.1:
        verdict["starmap_scope"] = "reduced"
        verdict["details"].append(
            f"主数据源 {best['source']} 宏观覆盖率偏低 ({best['macro_ratio']:.0%})，"
            "建议降低 news_score 权重或补充备选源"
        )
    else:
        verdict["starmap_scope"] = "minimal"
        verdict["details"].append("宏观新闻覆盖率不足，StarMap 降级为公告情感 + 纯量化")

    return verdict


async def main() -> None:
    """执行全部 PoC 测试并输出评估结论。"""
    print("=" * 70)
    print("StarMap Phase 0: 新闻源 PoC 验证")
    print(f"执行时间: {datetime.now().isoformat()}")
    print("=" * 70)

    # 并发测试所有数据源
    results = await asyncio.gather(
        test_tushare_news(),
        test_sina_7x24(),
        test_cls_telegraph(),
    )

    # 输出每个数据源结果
    for r in results:
        print(f"\n{'─' * 50}")
        print(f"📡 数据源: {r['source']}")
        print(f"   可达: {'✅' if r['reachable'] else '❌'}")
        print(f"   新闻条数: {r['news_count']}")
        print(f"   延迟: {r['latency_ms']}ms")
        print(f"   宏观覆盖率: {r['macro_ratio']:.0%}")

        if r.get("error"):
            print(f"   ❌ 错误: {r['error']}")
        if r.get("notes"):
            for note in r["notes"]:
                print(f"   📝 {note}")
        if r.get("sample_titles"):
            print("   📋 样例新闻:")
            for t in r["sample_titles"][:5]:
                print(f"      • {t}")
        if r.get("field_quality"):
            fq = r["field_quality"]
            print(f"   字段完整性: {fq.get('completeness', 0):.0%}")
            if fq.get("missing"):
                print(f"   缺失字段: {fq['missing']}")

    # 生成综合评估
    verdict = generate_poc_verdict(list(results))
    print(f"\n{'=' * 70}")
    print("📊 综合评估结论")
    print(f"{'=' * 70}")
    print(f"推荐主数据源: {verdict['recommended_primary'] or '无'}")
    print(f"推荐备选源: {verdict['recommended_fallback'] or '无'}")
    print(f"StarMap Scope: {verdict['starmap_scope']}")
    for d in verdict["details"]:
        print(f"  → {d}")

    # 保存结果到 JSON
    output = {
        "poc_results": [r for r in results],
        "verdict": verdict,
    }
    output_path = "docs/design/18-news-poc-result.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n✅ 结果已保存到 {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
