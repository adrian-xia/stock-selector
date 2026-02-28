"""每周全市场参数优化 cron 任务。

遍历启用的策略，对有 param_space 的策略逐个执行全市场选股回放优化，
最佳参数自动写入 strategies.params 表。
"""

import json
import logging
from datetime import date

from sqlalchemy import text

from app.config import settings
from app.database import async_session_factory
from app.optimization.market_optimizer import MarketOptimizer
from app.optimization.param_space import count_combinations
from app.strategy.factory import StrategyFactory

logger = logging.getLogger(__name__)


async def weekly_market_opt_job() -> None:
    """每周自动全市场参数优化。

    流程：
    1. 读取所有启用策略
    2. 过滤有 param_space 且组合数 <= 500 的策略
    3. 逐个执行全市场选股回放优化
    4. 最佳参数写入 strategies.params
    5. 结果写入 market_optimization_tasks 表
    6. 发送 Telegram 通知汇总
    """
    if not settings.market_opt_enabled:
        logger.info("全市场参数优化已禁用")
        return

    logger.info("=== 开始每周全市场参数优化 ===")

    # 获取启用的策略
    async with async_session_factory() as session:
        result = await session.execute(
            text("SELECT name FROM strategies WHERE is_enabled = true")
        )
        enabled_names = [row[0] for row in result.fetchall()]

    if not enabled_names:
        logger.info("无启用策略，跳过优化")
        return

    # 过滤有 param_space 的策略
    # 基本面策略 Layer 3 计算量过大，暂时跳过优化
    SKIP_STRATEGIES = {
        "growth-stock", "financial-safety", "pb-value", "peg-value",
        "ps-value", "high-dividend", "gross-margin-up", "cashflow-quality",
        "profit-continuous-growth", "cashflow-coverage", "quality-score",
        "low-pe-high-roe",
    }
    candidates: list[tuple[str, dict]] = []
    for name in enabled_names:
        try:
            meta = StrategyFactory.get_meta(name)
        except KeyError:
            continue
        if not meta.param_space:
            continue
        if name in SKIP_STRATEGIES:
            logger.info("策略 %s 为基本面策略，暂时跳过优化", name)
            continue
        combos = count_combinations(meta.param_space)
        if combos > settings.market_opt_max_combinations:
            logger.info("策略 %s 组合数 %d 超过 %d，跳过", name, combos, settings.market_opt_max_combinations)
            continue
        candidates.append((name, meta.param_space))

    if not candidates:
        logger.info("无可优化策略（无 param_space 或组合数过大）")
        return

    logger.info("待优化策略: %d 个", len(candidates))

    optimizer = MarketOptimizer(
        async_session_factory,
        max_concurrency=settings.market_opt_max_concurrency,
        sample_interval=settings.market_opt_sample_interval,
    )
    lookback = settings.market_opt_lookback_days
    auto_apply = settings.market_opt_auto_apply

    summary_lines: list[str] = []
    results_summary: list[dict] = []

    for strategy_name, param_space in candidates:
        total_combos = count_combinations(param_space)
        logger.info("优化策略: %s (组合数=%d)", strategy_name, total_combos)

        # 创建任务记录
        async with async_session_factory() as session:
            result = await session.execute(
                text("""
                    INSERT INTO market_optimization_tasks (
                        strategy_name, status, param_space, lookback_days,
                        total_combinations, auto_apply
                    ) VALUES (
                        :name, 'running', CAST(:ps AS jsonb),
                        :lookback, :combos, :auto_apply
                    )
                    RETURNING id
                """),
                {
                    "name": strategy_name,
                    "ps": json.dumps(param_space),
                    "lookback": lookback,
                    "combos": total_combos,
                    "auto_apply": auto_apply,
                },
            )
            task_id = result.scalar_one()
            await session.commit()

        try:
            results = await optimizer.optimize(
                strategy_name=strategy_name,
                param_space=param_space,
                lookback_days=lookback,
                top_n=10,
            )

            best_params = results[0].params if results else None
            best_score = results[0].score if results else None
            result_detail = [
                {
                    "rank": i + 1,
                    "params": r.params,
                    "hit_rate_5d": r.hit_rate_5d,
                    "avg_return_5d": r.avg_return_5d,
                    "max_drawdown": r.max_drawdown,
                    "total_picks": r.total_picks,
                    "score": r.score,
                }
                for i, r in enumerate(results)
            ]

            async with async_session_factory() as session:
                await session.execute(
                    text("""
                        UPDATE market_optimization_tasks
                        SET status = 'completed', progress = 100,
                            best_params = CAST(:best_params AS jsonb),
                            best_score = :best_score,
                            result_detail = CAST(:result_detail AS jsonb),
                            finished_at = NOW()
                        WHERE id = :task_id
                    """),
                    {
                        "task_id": task_id,
                        "best_params": json.dumps(best_params) if best_params else None,
                        "best_score": best_score,
                        "result_detail": json.dumps(result_detail),
                    },
                )

                # 自动应用最佳参数
                if auto_apply and best_params:
                    await session.execute(
                        text("""
                            UPDATE strategies SET params = CAST(:params AS jsonb), updated_at = NOW()
                            WHERE name = :name
                        """),
                        {"name": strategy_name, "params": json.dumps(best_params)},
                    )

                await session.commit()

            summary_lines.append(
                f"  {strategy_name}: score={best_score:.4f}, params={best_params}"
                if best_score else f"  {strategy_name}: 无有效结果"
            )
            results_summary.append({
                "strategy_name": strategy_name,
                "best_score": best_score,
                "best_params": best_params,
                "result_detail": result_detail,
            })
            logger.info("策略 %s 优化完成，最佳评分 %.4f", strategy_name, best_score or 0)

        except Exception as e:
            logger.exception("策略 %s 优化失败", strategy_name)
            async with async_session_factory() as session:
                await session.execute(
                    text("""
                        UPDATE market_optimization_tasks
                        SET status = 'failed', error_message = :error, finished_at = NOW()
                        WHERE id = :task_id
                    """),
                    {"task_id": task_id, "error": str(e)},
                )
                await session.commit()
            summary_lines.append(f"  {strategy_name}: 失败 - {e}")
            results_summary.append({
                "strategy_name": strategy_name,
                "error": str(e),
            })

    logger.info("=== 每周全市场参数优化完成 ===")

    # 发送 Telegram 通知（摘要 + Markdown 文件报告）
    try:
        from app.notification import NotificationManager
        from app.scheduler.report import generate_market_opt_report

        notifier = NotificationManager()
        summary_text, md_content = generate_market_opt_report(results_summary)
        await notifier.send_report(
            title="📊 每周全市场参数优化完成",
            summary_text=summary_text,
            markdown_content=md_content,
            filename=f"market_opt_{date.today()}.md",
        )
    except Exception as e:
        logger.warning("Telegram 通知发送失败: %s", e)
