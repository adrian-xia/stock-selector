"""测试 StarMap Markdown 报告生成。"""

from datetime import date
from types import SimpleNamespace

from app.scheduler.report import generate_starmap_report


def test_generate_starmap_report_contains_core_sections():
    """应生成完整的 StarMap Markdown 报告。"""
    result = {
        "status": "success",
        "steps_completed": ["readiness_probe", "news_pipeline", "plan_generator"],
        "degrade_flags": ["news_source_partial"],
        "errors": [],
        "stats": {
            "news_fetched": 18,
            "news_deduped": 12,
            "plans_generated": 2,
        },
    }
    macro_signal = SimpleNamespace(
        risk_appetite="high",
        global_risk_score=72.5,
        model_name="gemini-2.0-flash",
        prompt_version="v1",
        content_hash="abcdef1234567890abcdef",
        macro_summary="流动性改善，风险偏好回升，成长方向更占优。",
        positive_sectors=["半导体", "AI算力"],
        negative_sectors=["银行"],
        key_drivers=[{"title": "降准预期", "reason": "改善流动性"}],
    )
    sectors = [
        SimpleNamespace(
            sector_name="半导体",
            sector_code="885760",
            final_score=88.6,
            news_score=84.2,
            moneyflow_score=90.1,
            trend_score=86.5,
            confidence=91.0,
            drivers=["政策催化", "资金净流入"],
        )
    ]
    plans = [
        SimpleNamespace(
            ts_code="688981.SH",
            source_strategy="volume-breakout-trigger-v2",
            plan_type="breakout",
            plan_status="PENDING",
            confidence=92.3,
            position_suggestion=0.25,
            market_regime="bull",
            sector_name="半导体",
            entry_rule="突破前高后回踩确认不破，放量站稳",
            stop_loss_rule="跌破突破位 5%",
            take_profit_rule="盈利 8% 减半仓，15% 清仓",
            emergency_exit_text="跳空低开超过2%时离场",
            risk_flags=["高波动"],
            reasoning=["行业共振靠前", "策略分与资金分共振"],
        )
    ]

    summary_text, markdown = generate_starmap_report(
        trade_date=date(2026, 3, 7),
        elapsed=75.0,
        result=result,
        macro_signal=macro_signal,
        sectors=sectors,
        plans=plans,
    )

    assert "StarMap 盘后投研报告" in markdown
    assert "## 执行摘要" in markdown
    assert "## 宏观信号" in markdown
    assert "## 行业共振" in markdown
    assert "## 增强交易计划" in markdown
    assert "688981.SH" in markdown
    assert "半导体" in markdown
    assert "降准预期" in markdown
    assert "增强计划 1 条" in summary_text
    assert "降级标记 1 个" in summary_text
