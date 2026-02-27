"""定时任务定义：盘后链路、周末维护、失败重试等。"""

import logging
import time
import traceback
from datetime import date, datetime

from app.cache.redis_client import get_redis
from app.cache.tech_cache import refresh_all_tech_cache
from app.config import settings
from app.data.manager import DataManager
from app.data.tushare import TushareClient
from app.database import async_session_factory
from app.scheduler.task_logger import TaskLogger
from app.strategy.factory import StrategyFactory
from app.strategy.pipeline import execute_pipeline

logger = logging.getLogger(__name__)

# 全局 TaskLogger 实例
_task_logger = TaskLogger(async_session_factory)


def _build_manager() -> DataManager:
    """构造 DataManager 实例（使用 TushareClient）。"""
    client = TushareClient()
    return DataManager(
        session_factory=async_session_factory,
        clients={"tushare": client},
        primary="tushare",
    )


async def run_post_market_chain(target_date: date | None = None) -> None:
    """盘后链路：同步锁 → 股票列表 → 进度初始化 → 批量处理 → 完整性门控 → 策略 → 释放锁。

    使用进度表驱动，支持断点续传。任一关键步骤失败则中断链路。

    Args:
        target_date: 目标日期，默认今天
    """
    target = target_date or date.today()
    chain_start = time.monotonic()
    logger.info("===== [盘后链路] 开始：%s =====", target)

    manager = _build_manager()

    # 记录任务开始
    log_id = await _task_logger.start("post_market_pipeline", trade_date=target)

    # 步骤 0：交易日历更新（非关键，失败不阻断）
    calendar_start = time.monotonic()
    try:
        calendar_result = await manager.sync_trade_calendar()
        logger.info("[交易日历更新] 完成：%s，耗时 %.2fs", calendar_result, time.monotonic() - calendar_start)
    except Exception:
        logger.warning("[交易日历更新] 失败（继续执行），耗时 %.2fs\n%s", time.monotonic() - calendar_start, traceback.format_exc())

    # 交易日校验
    is_trading = await manager.is_trade_day(target)
    if not is_trading:
        logger.info("[盘后链路] 非交易日，跳过：%s", target)
        return

    # 获取同步锁
    if not await manager.acquire_sync_lock():
        logger.warning("[盘后链路] 同步锁被占用，跳过：%s", target)
        return

    try:
        # 步骤 1：更新股票列表
        stock_list_start = time.monotonic()
        try:
            stock_result = await manager.sync_stock_list()
            logger.info("[股票列表更新] 完成：%s，耗时 %.1fs", stock_result, time.monotonic() - stock_list_start)
        except Exception:
            logger.warning("[股票列表更新] 失败（继续执行），耗时 %.1fs\n%s", time.monotonic() - stock_list_start, traceback.format_exc())

        # 步骤 2：重置 stale 状态 + 初始化进度表 + 同步退市状态
        stale_count = await manager.reset_stale_status()
        if stale_count > 0:
            logger.info("[盘后链路] 重置 stale 状态：%d 条", stale_count)

        init_result = await manager.init_sync_progress()
        logger.info("[盘后链路] 进度表初始化：%s", init_result)

        delisted_result = await manager.sync_delisted_status()
        logger.info("[盘后链路] 退市状态同步：%s", delisted_result)

        # 步骤 3：批量数据拉取 + 指标计算（按日期批量拉，比逐只快 100 倍）
        step3_start = time.monotonic()
        try:
            sync_result = await manager.sync_daily_by_date([target])
            logger.info(
                "[盘后链路] 步骤 3 完成：%s，耗时 %.1fs",
                sync_result, time.monotonic() - step3_start,
            )
        except Exception:
            logger.warning(
                "[盘后链路] 步骤 3 失败（继续执行），耗时 %.1fs\n%s",
                time.monotonic() - step3_start, traceback.format_exc(),
            )

        # 步骤 3.1：P1 财务数据同步（按季度判断，非关键，失败不阻断）
        p1_start = time.monotonic()
        try:
            # 判断当前季度的报告期（上一季度末）
            # Q1(1-3月)→上年12.31, Q2(4-6月)→3.31, Q3(7-9月)→6.30, Q4(10-12月)→9.30
            month = target.month
            year = target.year
            if month <= 3:
                period = f"{year - 1}1231"
            elif month <= 6:
                period = f"{year}0331"
            elif month <= 9:
                period = f"{year}0630"
            else:
                period = f"{year}0930"

            # 每季度首月执行（1/4/7/10月），避免每天重复拉取
            if month in (1, 4, 7, 10):
                raw_result = await manager.sync_raw_fina(period)
                etl_result = await manager.etl_fina(period)
                logger.info(
                    "[P1财务数据] 完成（含财务三表）：period=%s, raw=%s, etl=%s，耗时 %.1fs",
                    period, raw_result, etl_result, time.monotonic() - p1_start,
                )
            else:
                logger.debug("[P1财务数据] 非季度首月，跳过")
        except Exception:
            logger.warning(
                "[P1财务数据] 失败（继续执行），耗时 %.1fs\n%s",
                time.monotonic() - p1_start, traceback.format_exc(),
            )

        # 步骤 3.5：P2 资金流向同步（非关键，失败不阻断）
        p2_start = time.monotonic()
        try:
            p2_result = await manager.sync_raw_tables("p2", target, target, mode="incremental")
            logger.info(
                "[P2资金流向] 完成：%s，耗时 %.1fs",
                p2_result, time.monotonic() - p2_start,
            )
        except Exception:
            logger.warning(
                "[P2资金流向] 失败（继续执行），耗时 %.1fs\n%s",
                time.monotonic() - p2_start, traceback.format_exc(),
            )

        # 步骤 3.6：P3 指数数据同步（非关键，失败不阻断）
        p3_start = time.monotonic()
        try:
            p3_result = await manager.sync_raw_tables("p3_daily", target, target, mode="incremental")
            logger.info(
                "[P3指数数据] 完成：%s，耗时 %.1fs",
                p3_result, time.monotonic() - p3_start,
            )
        except Exception:
            logger.warning(
                "[P3指数数据] 失败（继续执行），耗时 %.1fs\n%s",
                time.monotonic() - p3_start, traceback.format_exc(),
            )

        # 步骤 3.7：板块数据同步（非关键，失败不阻断）
        concept_start = time.monotonic()
        try:
            td_str = target.strftime("%Y%m%d")
            concept_daily = await manager.sync_concept_daily(trade_date=td_str)

            # 同步板块成分股（每周一执行，避免每天重复拉取）
            if target.weekday() == 0:  # 周一
                from sqlalchemy import text as sa_text
                async with async_session_factory() as session:
                    rows = await session.execute(
                        sa_text("SELECT ts_code FROM concept_index")
                    )
                    concept_codes = [r.ts_code for r in rows]
                member_ok, member_fail = 0, 0
                for code in concept_codes:
                    try:
                        await manager.sync_concept_member(code)
                        member_ok += 1
                    except Exception:
                        member_fail += 1
                logger.info("[板块成分股] 完成：成功 %d，失败 %d", member_ok, member_fail)

            concept_tech = await manager.update_concept_indicators(target)
            logger.info(
                "[板块数据同步] 完成：daily=%s, tech=%s，耗时 %.1fs",
                concept_daily, concept_tech, time.monotonic() - concept_start,
            )
        except Exception:
            logger.warning(
                "[板块数据同步] 失败（继续执行），耗时 %.1fs\n%s",
                time.monotonic() - concept_start, traceback.format_exc(),
            )

        # 步骤 3.8：P5 核心数据同步（非关键，失败不阻断）
        p5_start = time.monotonic()
        try:
            p5_result = await manager.sync_p5_core(target)
            logger.info(
                "[P5核心数据同步] 完成：%s，耗时 %.1fs",
                p5_result, time.monotonic() - p5_start,
            )
        except Exception:
            logger.warning(
                "[P5核心数据同步] 失败（继续执行），耗时 %.1fs\n%s",
                time.monotonic() - p5_start, traceback.format_exc(),
            )

        # 步骤 3.85：raw 追平检查（扫描 raw_sync_progress，补齐遗漏的表）
        gap_start = time.monotonic()
        try:
            gap_result = await manager.sync_raw_tables(
                "all", target, target, mode="gap_fill"
            )
            if gap_result:
                gap_filled = sum(
                    1 for v in gap_result.values()
                    if isinstance(v, dict) and v.get("rows", 0) > 0
                )
                logger.info(
                    "[raw追平检查] 完成：检查 %d 张表，补齐 %d 张，耗时 %.1fs",
                    len(gap_result), gap_filled, time.monotonic() - gap_start,
                )
        except Exception:
            logger.warning(
                "[raw追平检查] 失败（继续执行），耗时 %.1fs\n%s",
                time.monotonic() - gap_start, traceback.format_exc(),
            )

        # 步骤 3.9：新闻采集与情感分析（受 news_crawl_enabled 控制，失败不阻断）
        if settings.news_crawl_enabled:
            news_start = time.monotonic()
            try:
                from app.ai.news_analyzer import (
                    NewsSentimentAnalyzer,
                    aggregate_daily_sentiment,
                    save_announcements,
                    save_daily_sentiment,
                )
                from app.data.sources.fetcher import fetch_all_news

                # 获取活跃股票代码（取前 100 只热门股票）
                from sqlalchemy import text as sa_text
                async with async_session_factory() as session:
                    rows = await session.execute(
                        sa_text(
                            "SELECT ts_code FROM stocks "
                            "WHERE list_status = 'L' "
                            "ORDER BY ts_code LIMIT 100"
                        )
                    )
                    active_codes = [r.ts_code for r in rows]

                if active_codes:
                    # 采集新闻
                    raw_news = await fetch_all_news(active_codes, target)
                    logger.info("[新闻采集] 采集到 %d 条新闻", len(raw_news))

                    # 情感分析
                    analyzer = NewsSentimentAnalyzer()
                    analyzed = await analyzer.analyze(raw_news)

                    # 保存公告
                    saved_ann = await save_announcements(analyzed, async_session_factory)

                    # 聚合并保存每日情感
                    daily = aggregate_daily_sentiment(analyzed, target)
                    saved_daily = await save_daily_sentiment(daily, async_session_factory)

                    logger.info(
                        "[新闻舆情] 完成：采集 %d 条，保存公告 %d 条，每日聚合 %d 条，耗时 %.1fs",
                        len(raw_news), saved_ann, saved_daily,
                        time.monotonic() - news_start,
                    )
                else:
                    logger.info("[新闻舆情] 无活跃股票，跳过")
            except Exception:
                logger.warning(
                    "[新闻舆情] 失败（继续执行），耗时 %.1fs\n%s",
                    time.monotonic() - news_start, traceback.format_exc(),
                )
        else:
            logger.info("[新闻舆情] 未启用（news_crawl_enabled=false），跳过")

        # 步骤 4：缓存刷新（非关键，失败不阻断）
        await cache_refresh_step(target)

        # 步骤 5：完整性门控 → 策略执行/跳过
        summary = await manager.get_sync_summary(target)
        completion_rate = summary["completion_rate"]
        threshold = settings.data_completeness_threshold

        if completion_rate >= threshold:
            logger.info(
                "[完整性门控] 通过：完成率 %.1f%% >= 阈值 %.1f%%，执行策略",
                completion_rate * 100, threshold * 100,
            )
            picks = []
            plans = []
            try:
                picks = await pipeline_step(target)
            except Exception:
                logger.error("[盘后链路] 策略管道执行失败\n%s", traceback.format_exc())

            # 步骤 5.05：生成交易计划（非关键，失败不阻断）
            if picks:
                plan_start = time.monotonic()
                try:
                    from app.strategy.trade_plan import TradePlanGenerator
                    generator = TradePlanGenerator()
                    plans = await generator.generate(async_session_factory, picks, target)
                    logger.info(
                        "[交易计划] 生成完成：%d 条，耗时 %.1fs",
                        len(plans), time.monotonic() - plan_start,
                    )
                except Exception:
                    logger.warning(
                        "[交易计划] 生成失败（继续执行），耗时 %.1fs\n%s",
                        time.monotonic() - plan_start, traceback.format_exc(),
                    )

            # 步骤 5.1：回填选股收益率（非关键，失败不阻断）
            returns_start = time.monotonic()
            try:
                returns_result = await manager.update_pick_returns(target)
                logger.info(
                    "[选股收益回填] 完成：%s，耗时 %.1fs",
                    returns_result, time.monotonic() - returns_start,
                )
            except Exception:
                logger.warning(
                    "[选股收益回填] 失败（继续执行），耗时 %.1fs\n%s",
                    time.monotonic() - returns_start, traceback.format_exc(),
                )

            # 步骤 5.2：计算命中率统计（非关键，失败不阻断）
            stats_start = time.monotonic()
            try:
                stats_result = await manager.compute_hit_stats(target)
                logger.info(
                    "[命中率统计] 完成：%s，耗时 %.1fs",
                    stats_result, time.monotonic() - stats_start,
                )
            except Exception:
                logger.warning(
                    "[命中率统计] 失败（继续执行），耗时 %.1fs\n%s",
                    time.monotonic() - stats_start, traceback.format_exc(),
                )

            # 步骤 5.5：AI 分析（非关键，失败不阻断）
            if picks:
                ai_start = time.monotonic()
                try:
                    from app.ai.manager import get_ai_manager
                    ai_manager = get_ai_manager()
                    if ai_manager.is_enabled:
                        # 取 Top 30 候选股进行 AI 分析
                        top_picks = picks[:30]
                        # 构建 market_data（简化版，使用 pick 自身数据）
                        market_data = {
                            p.ts_code: {"close": p.close, "pct_chg": p.pct_chg}
                            for p in top_picks
                        }
                        analyzed = await ai_manager.analyze(top_picks, market_data, target)
                        # 获取 token 用量并持久化
                        token_usage = ai_manager._get_client().get_last_usage() if ai_manager._client else None
                        saved = await ai_manager.save_results(
                            analyzed, target, async_session_factory, token_usage
                        )
                        logger.info(
                            "[AI分析] 完成：分析 %d 只，持久化 %d 条，耗时 %.1fs",
                            len(top_picks), saved, time.monotonic() - ai_start,
                        )
                    else:
                        logger.info("[AI分析] 未启用，跳过")
                except Exception:
                    logger.warning(
                        "[AI分析] 失败（继续执行），耗时 %.1fs\n%s",
                        time.monotonic() - ai_start, traceback.format_exc(),
                    )
        else:
            logger.warning(
                "[完整性门控] 未通过：完成率 %.1f%% < 阈值 %.1f%%，跳过策略（总 %d，完成 %d，失败 %d）",
                completion_rate * 100, threshold * 100,
                summary["total"], summary["data_done"], summary["failed"],
            )

        # 步骤 6：完整性告警（超过截止时间且有失败记录）
        _check_completeness_deadline(summary, target)

    finally:
        await manager.release_sync_lock()

    elapsed = time.monotonic() - chain_start
    elapsed_minutes = int(elapsed / 60)
    elapsed_seconds = int(elapsed % 60)
    logger.info(
        "===== [盘后链路] 完成：%s，总耗时 %d分%d秒 (%.1fs) =====",
        target, elapsed_minutes, elapsed_seconds, elapsed,
    )

    # 步骤 7：发送 Telegram 通知（全面盘后分析报告）
    try:
        from app.notification import NotificationManager, NotificationLevel
        notifier = NotificationManager()
        pick_count = len(picks) if picks else 0
        plan_count = len(plans) if plans else 0

        msg_lines = [
            f"📅 盘后分析报告 — {target}",
            f"{'─' * 28}",
            "",
            "📊 执行概况",
            f"  ⏱ 总耗时: {elapsed_minutes}分{elapsed_seconds}秒",
            f"  📈 数据同步: {summary.get('data_done', 'N/A')} 只股票",
            f"  🎯 选股命中: {pick_count} 条",
            f"  📋 交易计划: {plan_count} 条",
        ]

        # 策略分布统计
        if picks:
            from collections import Counter
            strategy_counter = Counter()
            for p in picks:
                for s in p.matched_strategies:
                    strategy_counter[s] += 1
            msg_lines.append("")
            msg_lines.append(f"📌 策略分布（共 {len(strategy_counter)} 个策略命中）")
            for sname, cnt in strategy_counter.most_common(10):
                msg_lines.append(f"  • {sname}: {cnt} 只")
            if len(strategy_counter) > 10:
                msg_lines.append(f"  … 及其他 {len(strategy_counter) - 10} 个策略")

        # 涨跌幅分布
        if picks:
            up_count = sum(1 for p in picks if p.pct_chg > 0)
            down_count = sum(1 for p in picks if p.pct_chg < 0)
            flat_count = sum(1 for p in picks if p.pct_chg == 0)
            avg_chg = sum(p.pct_chg for p in picks) / len(picks)
            msg_lines.append("")
            msg_lines.append("📉 选股池涨跌分布")
            msg_lines.append(f"  🔴 上涨: {up_count}  🟢 下跌: {down_count}  ⚪ 平盘: {flat_count}")
            msg_lines.append(f"  📊 平均涨跌幅: {avg_chg:+.2f}%")

        # Top 10 候选
        if picks:
            msg_lines.append("")
            msg_lines.append("🏆 Top 10 候选")
            for i, p in enumerate(picks[:10], 1):
                name = getattr(p, 'name', '') or p.ts_code
                chg_str = f"{p.pct_chg:+.2f}%" if p.pct_chg else ""
                strats = ",".join(p.matched_strategies[:3])
                if len(p.matched_strategies) > 3:
                    strats += f"+{len(p.matched_strategies)-3}"
                msg_lines.append(
                    f"  {i}. {p.ts_code} {name}"
                    f"\n     收盘:{p.close} 涨跌:{chg_str} 得分:{p.weighted_score:.2f}"
                    f"\n     策略:{strats}"
                )

        # 交易计划摘要
        if plans:
            msg_lines.append("")
            msg_lines.append(f"📋 交易计划 Top 10（共 {plan_count} 条）")
            # plans 是 dict 列表
            for i, pl in enumerate(plans[:10], 1):
                code = pl.get('ts_code', '')
                trigger = pl.get('trigger_type', '')
                tp = pl.get('trigger_price')
                sl = pl.get('stop_loss')
                tkp = pl.get('take_profit')
                strategy = pl.get('source_strategy', '')
                tp_str = f"触发:{tp}" if tp else ""
                sl_str = f"止损:{sl}" if sl else ""
                tkp_str = f"止盈:{tkp}" if tkp else ""
                prices = " | ".join(filter(None, [tp_str, sl_str, tkp_str]))
                msg_lines.append(
                    f"  {i}. {code} [{trigger}]"
                    f"\n     {prices}"
                    f"\n     来源:{strategy}"
                )

        msg_lines.append("")
        msg_lines.append(f"{'─' * 28}")
        msg_lines.append("🤖 选股系统自动生成")

        await notifier.send(
            NotificationLevel.INFO,
            f"✅ 盘后链路完成 — {target}",
            "\n".join(msg_lines),
        )
        logger.info("[Telegram通知] 已发送")
    except Exception:
        logger.warning("[Telegram通知] 发送失败\n%s", traceback.format_exc())

    # 记录任务完成
    await _task_logger.finish(
        log_id,
        status="success",
        result_summary={"elapsed_seconds": round(elapsed, 1)},
    )


def _check_completeness_deadline(summary: dict, target_date: date) -> None:
    """检查完整性告警：超过截止时间且有失败记录时发出告警。

    Args:
        summary: get_sync_summary() 返回的摘要
        target_date: 目标日期
    """
    if summary["failed"] == 0:
        return

    deadline_str = settings.pipeline_completeness_deadline
    deadline_time = datetime.strptime(deadline_str, "%H:%M").time()
    current_time = datetime.now().time()

    if current_time >= deadline_time:
        logger.warning(
            "[完整性告警] %s 超过截止时间 %s，仍有 %d 只股票失败（完成率 %.1f%%）",
            target_date, deadline_str, summary["failed"],
            summary["completion_rate"] * 100,
        )


async def cache_refresh_step(target_date: date) -> None:
    """刷新技术指标缓存（非关键步骤，失败不阻断链路）。

    Args:
        target_date: 目标日期
    """
    redis = get_redis()
    if redis is None:
        logger.warning("[缓存刷新] Redis 不可用，跳过")
        return

    step_start = time.monotonic()
    logger.info("[缓存刷新] 开始：%s", target_date)

    try:
        count = await refresh_all_tech_cache(redis, async_session_factory)
        elapsed = time.monotonic() - step_start
        logger.info("[缓存刷新] 完成：%d 只股票，总耗时 %.1fs", count, elapsed)
    except Exception as e:
        elapsed = time.monotonic() - step_start
        logger.warning("[缓存刷新] 失败（耗时 %.1fs），策略管道将回源数据库：%s", elapsed, e)


async def pipeline_step(target_date: date) -> list:
    """执行策略管道：仅执行用户启用的策略（注册制）。

    从 strategies 表读取 is_enabled=True 的策略及其自定义参数，
    传递给 execute_pipeline 执行。

    Args:
        target_date: 目标日期

    Returns:
        候选股票列表（StockPick）
    """
    import json
    from sqlalchemy import text as sa_text

    step_start = time.monotonic()
    logger.info("[策略管道] 开始：%s", target_date)

    # 从 strategies 表查询启用的策略
    async with async_session_factory() as session:
        result = await session.execute(
            sa_text("SELECT name, params FROM strategies WHERE is_enabled = true")
        )
        rows = result.fetchall()

    if not rows:
        logger.warning("[策略管道] 没有启用的策略，跳过执行")
        return []

    strategy_names = []
    strategy_params: dict[str, dict] = {}
    for name, params_str in rows:
        # 校验策略在内存注册表中存在
        try:
            StrategyFactory.get_meta(name)
        except KeyError:
            logger.warning("[策略管道] 策略 %s 已启用但未注册，跳过", name)
            continue
        strategy_names.append(name)
        # 解析自定义参数
        if params_str:
            try:
                p = json.loads(params_str) if isinstance(params_str, str) else params_str
                if p:
                    strategy_params[name] = p
            except (json.JSONDecodeError, TypeError):
                pass

    if not strategy_names:
        logger.warning("[策略管道] 没有有效的启用策略，跳过执行")
        return []

    logger.info("[策略管道] 启用策略 %d 个：%s", len(strategy_names), strategy_names)

    result = await execute_pipeline(
        session_factory=async_session_factory,
        strategy_names=strategy_names,
        target_date=target_date,
        top_n=50,
        strategy_params=strategy_params or None,
    )

    elapsed = int(time.monotonic() - step_start)
    logger.info(
        "[策略管道] 完成：筛选出 %d 只，耗时 %dms",
        len(result.picks), result.elapsed_ms,
    )
    return result.picks


async def sync_stock_list_job() -> None:
    """周末股票列表全量同步。"""
    manager = _build_manager()

    # 步骤 1：更新交易日历
    logger.info("[交易日历更新] 开始")
    try:
        calendar_result = await manager.sync_trade_calendar()
        logger.info("[交易日历更新] 完成：%s", calendar_result)
    except Exception:
        logger.error("[交易日历更新] 失败，继续执行股票列表同步\n%s", traceback.format_exc())

    # 步骤 2：同步股票列表
    logger.info("[股票列表同步] 开始")
    result = await manager.sync_stock_list()
    logger.info("[股票列表同步] 完成：%s", result)


async def retry_failed_stocks_job() -> None:
    """定时重试失败股票：获取同步锁 → 查询失败股票 → 逐只重试 → 检查完整性 → 释放锁。

    每次重试 retry_count+1，超过 max_retries 的股票记录 WARNING 不再重试。
    重试完成后检查完整性，达到阈值则补跑策略。
    """
    target = date.today()
    start = time.monotonic()
    logger.info("[失败重试] 开始：%s", target)

    manager = _build_manager()
    max_retries = settings.batch_sync_max_retries

    # 获取同步锁
    if not await manager.acquire_sync_lock():
        logger.warning("[失败重试] 同步锁被占用，跳过")
        return

    try:
        # 查询可重试的失败股票
        failed_stocks = await manager.get_failed_stocks(max_retries)
        if not failed_stocks:
            logger.info("[失败重试] 无需重试的失败股票")
            return

        logger.info("[失败重试] 待重试股票 %d 只", len(failed_stocks))

        # 检查超过重试上限的股票
        all_failed = await manager.get_failed_stocks(max_retries=999999)
        exceeded = [s for s in all_failed if s["retry_count"] >= max_retries]
        if exceeded:
            codes = [s["ts_code"] for s in exceeded[:10]]
            logger.warning(
                "[失败重试] %d 只股票超过最大重试次数 %d，不再自动重试：%s%s",
                len(exceeded), max_retries, codes,
                "..." if len(exceeded) > 10 else "",
            )

        # 递增 retry_count 并重置状态为 idle，然后重新处理
        from sqlalchemy import update as sa_update
        from app.models.market import StockSyncProgress

        success_count = 0
        fail_count = 0
        for stock in failed_stocks:
            ts_code = stock["ts_code"]
            try:
                # 递增 retry_count
                async with manager.session_factory() as session:
                    await session.execute(
                        sa_update(StockSyncProgress)
                        .where(StockSyncProgress.ts_code == ts_code)
                        .values(retry_count=StockSyncProgress.retry_count + 1, status="idle")
                    )
                    await session.commit()

                # 从 data_date 恢复同步
                await manager.process_single_stock(ts_code, target)
                success_count += 1
            except Exception as e:
                fail_count += 1
                logger.error("[失败重试] %s 重试失败：%s", ts_code, e)

        elapsed = time.monotonic() - start
        logger.info(
            "[失败重试] 完成：成功 %d，失败 %d，耗时 %.1fs",
            success_count, fail_count, elapsed,
        )

        # 重试后检查完整性，达到阈值则补跑策略
        summary = await manager.get_sync_summary(target)
        completion_rate = summary["completion_rate"]
        threshold = settings.data_completeness_threshold

        if completion_rate >= threshold:
            logger.info(
                "[失败重试] 完成率 %.1f%% >= 阈值 %.1f%%，补跑策略",
                completion_rate * 100, threshold * 100,
            )
            try:
                await pipeline_step(target)
            except Exception:
                logger.error("[失败重试] 补跑策略失败\n%s", traceback.format_exc())
        else:
            logger.info(
                "[失败重试] 完成率 %.1f%% < 阈值 %.1f%%，跳过策略",
                completion_rate * 100, threshold * 100,
            )

    finally:
        await manager.release_sync_lock()
