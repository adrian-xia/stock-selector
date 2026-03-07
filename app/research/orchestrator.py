"""StarMap Orchestrator：盘后投研主编排器。

按设计文档 §9 编排完整 StarMap 流程：
1. 清理过期计划
2. 就绪探针
3. 新闻抓取 + 清洗 + 去重
4. LLM 结构化提取
5. 行业对齐
6. 市场评分
7. 行业共振
8. 个股融合排序
9. 计划生成
10. 数据落库

每个模块失败不阻断主链路（降级矩阵 §10）。
"""

import hashlib
import json
import logging
from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)


async def run_starmap(
    session_factory: async_sessionmaker[AsyncSession],
    trade_date: date,
) -> dict:
    """执行完整 StarMap 盘后投研流程。

    Args:
        session_factory: 数据库会话工厂
        trade_date: 目标交易日

    Returns:
        执行结果摘要字典
    """
    result = {
        "trade_date": trade_date.isoformat(),
        "started_at": datetime.now().isoformat(),
        "status": "success",
        "steps_completed": [],
        "degrade_flags": [],
        "errors": [],
        "stats": {},
    }

    logger.info("=" * 60)
    logger.info("[StarMap] 开始盘后投研: %s", trade_date)
    logger.info("=" * 60)

    # ── Step 0: 清理过期计划 ─────────────────────────────
    try:
        from app.research.planner.rule_engine import expire_pending_plans

        expired = await expire_pending_plans(session_factory, trade_date)
        result["stats"]["expired_plans"] = expired
        result["steps_completed"].append("expire_plans")
    except Exception as e:
        logger.warning("[StarMap] 清理过期计划失败（不阻断）: %s", e)
        result["errors"].append(f"expire_plans: {e}")

    # ── Step 1: 就绪探针 ─────────────────────────────────
    degrade_flags: list[str] = []
    try:
        from app.research.probe.readiness import check_readiness

        readiness = await check_readiness(session_factory, trade_date)
        degrade_flags = readiness.degrade_flags
        result["stats"]["news_count_existing"] = readiness.news_count

        if not readiness.ready:
            logger.warning("[StarMap] 就绪探针未通过: %s", readiness.missing)
            result["degrade_flags"].extend(degrade_flags)
            # 不阻断，但记录降级标记

        result["steps_completed"].append("readiness_probe")
    except Exception as e:
        logger.warning("[StarMap] 就绪探针失败（降级运行）: %s", e)
        result["errors"].append(f"readiness_probe: {e}")

    # ── Step 2: 新闻抓取 + 清洗 + 去重 ──────────────────
    cleaned_news: list[dict] = []
    content_hash_combined = ""
    try:
        from app.research.news.fetcher import fetch_macro_news

        raw_items = await fetch_macro_news(trade_date, max_items=80)
        result["stats"]["news_fetched"] = len(raw_items)

        if raw_items:
            # 转换为 dict 列表
            news_dicts = [
                {"title": item.title, "content": item.content,
                 "pub_time": item.pub_time.isoformat(), "source": item.source}
                for item in raw_items
            ]

            # 清洗
            from app.research.news.cleaner import clean_news_batch
            cleaned_news = clean_news_batch(news_dicts)
            result["stats"]["news_cleaned"] = len(cleaned_news)

            # 去重
            from app.research.news.dedupe import dedupe_news
            cleaned_news = dedupe_news(cleaned_news)
            result["stats"]["news_deduped"] = len(cleaned_news)

            # 计算内容哈希
            combined_text = "".join(n.get("content", "") for n in cleaned_news)
            content_hash_combined = hashlib.sha256(
                combined_text.encode("utf-8")
            ).hexdigest()

        result["steps_completed"].append("news_pipeline")
    except Exception as e:
        logger.warning("[StarMap] 新闻管道失败（降级至纯量化）: %s", e)
        result["errors"].append(f"news_pipeline: {e}")
        degrade_flags.append("NEWS_PIPELINE_FAILED")

    # ── Step 3: LLM 结构化提取 ───────────────────────────
    macro_signal = None
    positive_sectors_aligned: list[dict] = []
    negative_sectors_aligned: list[dict] = []

    if cleaned_news and "NEWS_PIPELINE_FAILED" not in degrade_flags:
        try:
            from app.research.llm.prompts import build_macro_prompt, PROMPT_VERSION
            from app.research.llm.parser import build_default_signal
            from app.research.llm.schema import MacroSignalOutput

            prompt = build_macro_prompt(cleaned_news)

            # 调用 LLM（复用现有 AI 客户端体系）
            from app.ai.gateway import AIRequest, get_ai_gateway

            gateway = get_ai_gateway()
            if gateway.is_enabled:
                ai_response = await gateway.execute(
                    AIRequest(
                        prompt=prompt,
                        response_format="json",
                        task_name="starmap_macro_signal",
                    )
                )
                if ai_response.ok and ai_response.content is not None:
                    macro_signal = MacroSignalOutput.model_validate(ai_response.content)
                    result["stats"]["llm_invoked"] = True

            if macro_signal is None:
                macro_signal = build_default_signal()
                result["degrade_flags"].append("LLM_FALLBACK")

            # 行业对齐
            from app.research.llm.aligner import align_sector

            for sector in macro_signal.positive_sectors:
                code, name = align_sector(sector.sector_name)
                positive_sectors_aligned.append({
                    "sector_code": code,
                    "sector_name": name or sector.sector_name,
                    "reason": sector.reason,
                    "confidence": sector.confidence,
                })

            for sector in macro_signal.negative_sectors:
                code, name = align_sector(sector.sector_name)
                negative_sectors_aligned.append({
                    "sector_code": code,
                    "sector_name": name or sector.sector_name,
                    "reason": sector.reason,
                    "confidence": sector.confidence,
                })

            result["steps_completed"].append("llm_extraction")
        except Exception as e:
            logger.warning("[StarMap] LLM 提取失败（降级纯量化）: %s", e)
            result["errors"].append(f"llm_extraction: {e}")
            degrade_flags.append("LLM_FAILED")
    else:
        logger.info("[StarMap] 跳过 LLM（无新闻数据）")
        degrade_flags.append("NO_NEWS_DATA")

    # ── Step 4: 宏观信号落库 ─────────────────────────────
    if macro_signal:
        try:
            from app.research.repository.starmap_repo import StarMapRepository

            repo = StarMapRepository(session_factory)
            await repo.upsert_macro_signal({
                "trade_date": trade_date,
                "risk_appetite": macro_signal.risk_appetite,
                "global_risk_score": macro_signal.global_risk_score,
                "positive_sectors": [s.model_dump() for s in macro_signal.positive_sectors],
                "negative_sectors": [s.model_dump() for s in macro_signal.negative_sectors],
                "macro_summary": macro_signal.macro_summary,
                "key_drivers": [d.model_dump() for d in macro_signal.key_drivers],
                "raw_payload": {"news_count": len(cleaned_news), "degrade_flags": degrade_flags},
                "content_hash": content_hash_combined or "no-news",
                "model_name": settings.codex_model_id,
                "prompt_version": "v1.0",
            })
            result["steps_completed"].append("macro_signal_persist")
        except Exception as e:
            logger.warning("[StarMap] 宏观信号落库失败: %s", e)
            result["errors"].append(f"macro_signal_persist: {e}")

    # ── Step 5: 市场评分 ─────────────────────────────────
    market_regime = None
    try:
        from app.research.scoring.market_regime import calc_market_regime

        market_regime = await calc_market_regime(session_factory, trade_date)
        result["stats"]["market_risk_score"] = market_regime.risk_score
        result["stats"]["market_regime"] = market_regime.market_regime
        result["steps_completed"].append("market_regime")
    except Exception as e:
        logger.warning("[StarMap] 市场评分失败: %s", e)
        result["errors"].append(f"market_regime: {e}")

    # ── Step 6: 行业共振 ─────────────────────────────────
    sector_scores: dict[str, float] = {}
    try:
        from app.research.scoring.sector_resonance import calc_sector_resonance

        sector_results = await calc_sector_resonance(
            session_factory, trade_date,
            positive_sectors_aligned, negative_sectors_aligned,
        )
        sector_scores = {s.sector_code: s.final_score for s in sector_results}
        result["stats"]["sector_count"] = len(sector_results)

        # 落库
        from app.research.repository.starmap_repo import StarMapRepository

        repo = StarMapRepository(session_factory)
        sector_dicts = [
            {
                "trade_date": trade_date,
                "sector_code": s.sector_code,
                "sector_name": s.sector_name,
                "news_score": s.news_score,
                "moneyflow_score": s.moneyflow_score,
                "trend_score": s.trend_score,
                "final_score": s.final_score,
                "confidence": s.confidence,
                "drivers": s.drivers,
            }
            for s in sector_results[:50]  # Top 50
        ]
        await repo.upsert_sector_resonance_batch(sector_dicts)
        result["steps_completed"].append("sector_resonance")
    except Exception as e:
        logger.warning("[StarMap] 行业共振失败: %s", e)
        result["errors"].append(f"sector_resonance: {e}")

    # ── Step 7: 个股融合排序 ──────────────────────────────
    ranked_stocks = []
    try:
        from app.research.scoring.stock_rank_fusion import calc_stock_rank_fusion

        ranked_stocks = await calc_stock_rank_fusion(
            session_factory, trade_date, sector_scores, top_n=30,
        )
        result["stats"]["ranked_stocks"] = len(ranked_stocks)
        result["steps_completed"].append("stock_rank_fusion")
    except Exception as e:
        logger.warning("[StarMap] 个股融合失败: %s", e)
        result["errors"].append(f"stock_rank_fusion: {e}")

    # ── Step 8: 计划生成 + 落库 ───────────────────────────
    if ranked_stocks and market_regime:
        try:
            from app.research.planner.plan_generator import generate_trade_plans

            repo = StarMapRepository(session_factory)
            valid_date = await repo.get_next_trade_date(trade_date)
            plans = generate_trade_plans(
                ranked_stocks, market_regime, sector_scores, trade_date, valid_date,
            )
            result["stats"]["plans_generated"] = len(plans)

            # 落库
            await repo.upsert_trade_plans_batch(plans)
            result["steps_completed"].append("plan_generation")
        except Exception as e:
            logger.warning("[StarMap] 计划生成失败: %s", e)
            result["errors"].append(f"plan_generation: {e}")

    # ── 完成 ─────────────────────────────────────────────
    result["finished_at"] = datetime.now().isoformat()
    result["degrade_flags"] = degrade_flags

    if result["errors"]:
        result["status"] = "partial" if result["steps_completed"] else "failed"

    logger.info(
        "[StarMap] 完成: status=%s steps=%d errors=%d flags=%s",
        result["status"], len(result["steps_completed"]),
        len(result["errors"]), degrade_flags,
    )
    return result
