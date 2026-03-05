"""StarMap 核心模块单元测试。

覆盖：去重、清洗、对齐、LLM 解析、归一化、计划生成。
不依赖数据库或外部服务。
"""

import pytest

from app.research.news.dedupe import content_hash, dedupe_news, _jaccard, _tokenize
from app.research.news.cleaner import clean_news_item, clean_news_batch
from app.research.llm.aligner import align_sector, align_sectors_batch
from app.research.llm.parser import parse_macro_signal, extract_json, build_default_signal
from app.research.llm.schema import MacroSignalOutput, SectorImpact, KeyDriver
from app.research.llm.prompts import build_macro_prompt, PROMPT_VERSION
from app.research.scoring.normalize import percentile_rank, min_max_scale, normalize_scores


# ===== 去重 =====

class TestDedupe:
    def test_exact_dedup(self):
        items = [
            {"content": "央行降准50个基点"},
            {"content": "央行降准50个基点"},
            {"content": "沪指收涨0.5%"},
        ]
        result = dedupe_news(items)
        assert len(result) == 2

    def test_fuzzy_dedup(self):
        items = [
            {"content": "央行宣布降低存款准备金率50个基点释放流动性约1万亿元"},
            {"content": "央行宣布降低存款准备金率50个基点释放流动性约一万亿"},
            {"content": "沪指今日收涨百分之零点五创业板指收跌百分之零点三"},
        ]
        result = dedupe_news(items)
        # 前两条应被去重（Jaccard > 0.7）
        assert len(result) == 2

    def test_empty_input(self):
        assert dedupe_news([]) == []

    def test_single_item(self):
        items = [{"content": "测试"}]
        assert len(dedupe_news(items)) == 1

    def test_content_hash_consistency(self):
        h1 = content_hash("hello")
        h2 = content_hash("hello")
        h3 = content_hash("world")
        assert h1 == h2
        assert h1 != h3

    def test_jaccard_same(self):
        s = {"a", "b", "c"}
        assert _jaccard(s, s) == 1.0

    def test_jaccard_disjoint(self):
        assert _jaccard({"a", "b"}, {"c", "d"}) == 0.0


# ===== 清洗 =====

class TestCleaner:
    def test_strip_html(self):
        item = {"title": "<b>标题</b>", "content": "<p>正文&amp;内容</p>"}
        cleaned = clean_news_item(item)
        assert "<" not in cleaned["title"]
        assert "&amp;" not in cleaned["content"]
        assert "正文" in cleaned["content"]

    def test_truncation(self):
        item = {"title": "标题", "content": "字" * 5000}
        cleaned = clean_news_item(item)
        assert len(cleaned["content"]) <= 2200  # ~2000 + 句边界容差

    def test_whitespace_normalization(self):
        item = {"title": "  多  个   空格  ", "content": "换\n  行\t制表"}
        cleaned = clean_news_item(item)
        assert "  " not in cleaned["title"]

    def test_batch(self):
        items = [{"title": f"title{i}", "content": f"这是一段比较长的新闻内容第{i}条"} for i in range(5)]
        result = clean_news_batch(items)
        assert len(result) == 5


# ===== 行业对齐 =====

class TestAligner:
    def test_exact_match(self):
        code, name = align_sector("半导体")
        assert code is not None  # may come from THS or SW
        assert name is not None

    def test_contains_match(self):
        code, name = align_sector("新能源汽车产业链")
        # "新能源" matches first in dict iteration - exact behavior depends on dict order
        assert code is not None  # should match something

    def test_reverse_contains(self):
        code, name = align_sector("AI")
        assert code == "885760"

    def test_unknown_sector(self):
        code, name = align_sector("外星科技")
        assert code is None
        assert name is None

    def test_batch(self):
        results = align_sectors_batch(["半导体", "外星科技", "银行"])
        assert len(results) == 3
        assert results[0]["resolved"] is True
        assert results[1]["resolved"] is False
        assert results[2]["resolved"] is True


# ===== LLM 解析 =====

class TestParser:
    def test_parse_valid_json(self):
        raw = '{"risk_appetite":"high","global_risk_score":75,"macro_summary":"测试","positive_sectors":[],"negative_sectors":[],"key_drivers":[]}'
        result = parse_macro_signal(raw)
        assert result is not None
        assert result.risk_appetite == "high"
        assert result.global_risk_score == 75

    def test_parse_with_markdown_wrapper(self):
        raw = '```json\n{"risk_appetite":"low","global_risk_score":25,"macro_summary":"利好","positive_sectors":[],"negative_sectors":[],"key_drivers":[]}\n```'
        result = parse_macro_signal(raw)
        assert result is not None
        assert result.risk_appetite == "low"

    def test_parse_chinese_values(self):
        """测试中文 risk_appetite 自动修复。"""
        raw = '{"risk_appetite":"高","global_risk_score":80,"macro_summary":"市场高风险","positive_sectors":[],"negative_sectors":[],"key_drivers":[]}'
        result = parse_macro_signal(raw)
        assert result is not None
        assert result.risk_appetite in ("high", "mid", "low")

    def test_parse_invalid_returns_none(self):
        """无效输入时 parser 返回 None（调用方决定是否用默认值）。"""
        result = parse_macro_signal("这不是JSON")
        assert result is None

    def test_build_default_signal(self):
        sig = build_default_signal()
        assert sig.risk_appetite == "mid"
        assert sig.global_risk_score == 50.0
        assert "不足" in sig.macro_summary or "默认" in sig.macro_summary

    def test_extract_json_from_text(self):
        text = '前面的话 {"key": "value"} 后面的话'
        result = extract_json(text)
        assert result is not None
        assert "key" in result


# ===== Schema =====

class TestSchema:
    def test_valid_signal(self):
        sig = MacroSignalOutput(
            risk_appetite="mid",
            global_risk_score=55,
            positive_sectors=[SectorImpact(sector_name="新能源", reason="政策", confidence=0.8)],
            negative_sectors=[],
            macro_summary="摘要",
            key_drivers=[KeyDriver(event="降息", impact="positive", magnitude="high")],
        )
        assert sig.risk_appetite == "mid"
        assert len(sig.positive_sectors) == 1

    def test_risk_appetite_validation(self):
        with pytest.raises(Exception):
            MacroSignalOutput(
                risk_appetite="invalid",
                global_risk_score=50,
                positive_sectors=[],
                negative_sectors=[],
                macro_summary="",
                key_drivers=[],
            )

    def test_score_bounds(self):
        with pytest.raises(Exception):
            MacroSignalOutput(
                risk_appetite="mid",
                global_risk_score=150,  # > 100
                positive_sectors=[],
                negative_sectors=[],
                macro_summary="",
                key_drivers=[],
            )


# ===== 归一化 =====

class TestNormalize:
    def test_percentile_rank_basic(self):
        vals = list(range(1, 31))  # 30 items
        result = percentile_rank(vals)
        assert len(result) == 30
        assert result[0] < result[-1]
        assert result[-1] == 100.0

    def test_small_sample_fallback(self):
        vals = [10, 20, 30]
        result = percentile_rank(vals, min_samples=30)
        # Should use min-max
        assert result == [0.0, 50.0, 100.0]

    def test_empty(self):
        assert percentile_rank([]) == []

    def test_single(self):
        assert percentile_rank([42]) == [50.0]

    def test_min_max_identical(self):
        result = min_max_scale([5, 5, 5])
        assert all(v == 50.0 for v in result)

    def test_normalize_scores_dict(self):
        scores = {f"s{i}": float(i) for i in range(30)}
        result = normalize_scores(scores)
        assert len(result) == 30
        assert max(result.values()) == 100.0


# ===== Prompts =====

class TestPrompts:
    def test_build_macro_prompt(self):
        news = [
            {"title": "央行降准", "content": "央行宣布降准50个基点"},
            {"title": "沪指收涨", "content": "沪指今日收涨0.5%"},
        ]
        prompt = build_macro_prompt(news)
        assert "央行降准" in prompt
        assert "risk_appetite" in prompt

    def test_prompt_version(self):
        assert PROMPT_VERSION is not None
        assert len(PROMPT_VERSION) > 0

    def test_empty_news(self):
        prompt = build_macro_prompt([])
        assert "risk_appetite" in prompt  # prompt template still present
