"""Telegram 报告生成模块：为定时任务生成摘要文本 + Markdown 完整报告。

每个函数返回 (summary_text, markdown_content) 元组：
- summary_text: 短摘要，直接作为 Telegram 文本消息发送
- markdown_content: 完整报告，作为 .md 文件附件发送
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import date
from typing import Any

logger = logging.getLogger(__name__)


def _get_strategy_display_names() -> dict[str, str]:
    """获取策略英文名 → 中文名映射。"""
    try:
        from app.strategy.factory import STRATEGY_REGISTRY
        return {name: meta.display_name for name, meta in STRATEGY_REGISTRY.items()}
    except Exception:
        return {}


def _display(name: str, name_map: dict[str, str]) -> str:
    """返回 '中文名(英文名)' 格式，找不到中文名则返回英文名。"""
    cn = name_map.get(name)
    return f"{cn}({name})" if cn else name


V4_STRATEGY_NAME = "volume-price-pattern"


def generate_post_market_report(
    target_date: date,
    elapsed: float,
    summary: dict[str, Any],
    picks: list[Any],
    plans: list[dict[str, Any]],
    watchpool: list[tuple] | None = None,
) -> tuple[str, str]:
    """生成盘后链路报告。"""
    name_map = _get_strategy_display_names()
    elapsed_min = int(elapsed / 60)
    elapsed_sec = int(elapsed % 60)
    pick_count = len(picks) if picks else 0
    plan_count = len(plans) if plans else 0
    _pool = watchpool or []

    # 检测 V4 策略命中
    v4_picks = [p for p in picks if V4_STRATEGY_NAME in p.matched_strategies] if picks else []
    v4_plans = [pl for pl in plans if pl.get("source_strategy") == V4_STRATEGY_NAME] if plans else []

    # ── 摘要文本 ──
    lines = [
        f"⏱ 耗时 {elapsed_min}分{elapsed_sec}秒 | 同步 {summary.get('data_done', 'N/A')} 只",
        f"🎯 选股 {pick_count} 条 | 交易计划 {plan_count} 条",
        f"📈 完成率 {summary.get('completion_rate', 0) * 100:.1f}%",
    ]
    if v4_picks:
        lines.append(f"🐉 V4量价配合(龙回头) 命中 {len(v4_picks)} 只")
    summary_text = "\n".join(lines)

    # ── Markdown 完整报告 ──
    md = [f"# 盘后分析报告 — {target_date}\n"]

    # 执行概况
    md.append("## 执行概况\n")
    md.append("| 指标 | 值 |")
    md.append("|------|-----|")
    md.append(f"| 总耗时 | {elapsed_min}分{elapsed_sec}秒 |")
    md.append(f"| 数据同步 | {summary.get('data_done', 'N/A')} 只 |")
    md.append(f"| 完成率 | {summary.get('completion_rate', 0) * 100:.1f}% |")
    md.append(f"| 失败数 | {summary.get('failed', 0)} |")
    md.append(f"| 选股命中 | {pick_count} 条 |")
    md.append(f"| 交易计划 | {plan_count} 条 |")
    md.append("")

    # ★ V4 量价配合策略专区（始终显示）
    md.append("## 🐉 V4 量价配合策略（龙回头）\n")
    md.append("> 策略逻辑：放量突破(T0) → 缩量回踩 → 企稳买入(Tk)")
    md.append("> 回测验证：5 日胜率 59%，盈亏比 1.87，夏普 2.21\n")

    if v4_picks:
        md.append(f"**🔥 今日命中 {len(v4_picks)} 只 — 重点关注！**\n")
        md.append("| 排名 | 代码 | 名称 | 收盘 | 涨跌幅 | 加权得分 |")
        md.append("|------|------|------|------|--------|----------|")
        for i, p in enumerate(v4_picks, 1):
            name = getattr(p, "name", "") or p.ts_code
            chg = f"{p.pct_chg:+.2f}%" if p.pct_chg else "0.00%"
            md.append(f"| {i} | {p.ts_code} | {name} | {p.close} | {chg} | {p.weighted_score:.2f} |")
        md.append("")
    else:
        md.append("今日无 V4 信号。该策略需要特定量价模式（放量突破→缩量回踩→企稳），")
        md.append("并非每日都有信号，属于正常情况。\n")

    # V4 watchpool 状态
    if _pool:
        md.append("### Watchpool 监控池\n")
        md.append("| 代码 | T0 日期 | 当前状态 | 洗盘天数 |")
        md.append("|------|---------|----------|----------|")
        for row in _pool:
            md.append(f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} |")
        md.append("")

    if v4_plans:
        md.append("### V4 交易计划\n")
        md.append("| 代码 | 触发类型 | 触发价 | 止损 | 止盈 | 信心 |")
        md.append("|------|----------|--------|------|------|------|")
        for pl in v4_plans:
            code = pl.get("ts_code", "")
            trigger = pl.get("trigger_type", "")
            tp = pl.get("trigger_price", "")
            sl = pl.get("stop_loss", "")
            tkp = pl.get("take_profit", "")
            conf = pl.get("confidence", "")
            md.append(f"| {code} | {trigger} | {tp} | {sl} | {tkp} | {conf} |")
        md.append("")

    # 策略分布
    if picks:
        strategy_counter: Counter[str] = Counter()
        for p in picks:
            for s in p.matched_strategies:
                strategy_counter[s] += 1

        md.append(f"## 策略分布（{len(strategy_counter)} 个策略命中）\n")
        md.append("| 策略 | 中文名 | 命中数 |")
        md.append("|------|--------|--------|")
        for sname, cnt in strategy_counter.most_common():
            cn = name_map.get(sname, "—")
            marker = " 🐉" if sname == V4_STRATEGY_NAME else ""
            md.append(f"| {sname} | {cn}{marker} | {cnt} |")
        md.append("")

    # 涨跌分布
    if picks and len(picks) > 0:
        up = sum(1 for p in picks if p.pct_chg > 0)
        down = sum(1 for p in picks if p.pct_chg < 0)
        flat = sum(1 for p in picks if p.pct_chg == 0)
        avg_chg = sum(p.pct_chg for p in picks) / len(picks)
        md.append("## 涨跌分布\n")
        md.append("| 指标 | 值 |")
        md.append("|------|-----|")
        md.append(f"| 上涨 | {up} |")
        md.append(f"| 下跌 | {down} |")
        md.append(f"| 平盘 | {flat} |")
        md.append(f"| 平均涨跌幅 | {avg_chg:+.2f}% |")
        md.append("")

    # 选股明细
    if picks:
        md.append(f"## 选股明细（共 {pick_count} 条）\n")
        md.append("| 排名 | 代码 | 名称 | 收盘 | 涨跌幅 | 加权得分 | 策略 |")
        md.append("|------|------|------|------|--------|----------|------|")
        for i, p in enumerate(picks, 1):
            name = getattr(p, "name", "") or p.ts_code
            chg = f"{p.pct_chg:+.2f}%" if p.pct_chg else "0.00%"
            strats = ", ".join(_display(s, name_map) for s in p.matched_strategies)
            md.append(
                f"| {i} | {p.ts_code} | {name} | {p.close} | {chg} "
                f"| {p.weighted_score:.2f} | {strats} |"
            )
        md.append("")

    # 交易计划
    if plans:
        md.append(f"## 交易计划（共 {plan_count} 条）\n")
        md.append("| 序号 | 代码 | 触发类型 | 触发价 | 止损 | 止盈 | 来源策略 |")
        md.append("|------|------|----------|--------|------|------|----------|")
        for i, pl in enumerate(plans, 1):
            code = pl.get("ts_code", "")
            trigger = pl.get("trigger_type", "")
            tp = pl.get("trigger_price", "")
            sl = pl.get("stop_loss", "")
            tkp = pl.get("take_profit", "")
            strategy = _display(pl.get("source_strategy", ""), name_map)
            md.append(f"| {i} | {code} | {trigger} | {tp} | {sl} | {tkp} | {strategy} |")
        md.append("")

    md.append("---\n*选股系统自动生成*\n")
    return summary_text, "\n".join(md)


def generate_market_opt_report(
    results_by_strategy: list[dict[str, Any]],
) -> tuple[str, str]:
    """生成全市场参数优化报告。"""
    name_map = _get_strategy_display_names()
    total = len(results_by_strategy)
    succeeded = [r for r in results_by_strategy if r.get("best_score") is not None]
    failed = [r for r in results_by_strategy if r.get("error")]

    # ── 摘要文本 ──
    if succeeded:
        scores = [r["best_score"] for r in succeeded]
        score_range = f"{min(scores):.4f} ~ {max(scores):.4f}"
        summary_text = (
            f"📊 优化 {total} 个策略，成功 {len(succeeded)} 个"
            f"\n🏆 最佳评分范围: {score_range}"
        )
        # 列出 Top 3
        top3 = sorted(succeeded, key=lambda r: r["best_score"], reverse=True)[:3]
        for i, r in enumerate(top3, 1):
            sn = r.get("strategy_name", "")
            cn = name_map.get(sn, sn)
            summary_text += f"\n  {i}. {cn}: {r['best_score']:.4f}"
    else:
        summary_text = f"📊 优化 {total} 个策略，全部失败"

    if failed:
        summary_text += f"\n⚠️ 失败 {len(failed)} 个"

    # ── Markdown 完整报告 ──
    md = ["# 全市场参数优化报告\n"]

    md.append("## 概况\n")
    md.append(f"- 优化策略数: {total}")
    md.append(f"- 成功: {len(succeeded)}")
    md.append(f"- 失败: {len(failed)}")
    md.append("")

    # 总排行榜
    if succeeded:
        ranked = sorted(succeeded, key=lambda r: r["best_score"], reverse=True)
        md.append("## 策略评分排行\n")
        md.append("| 排名 | 策略 | 中文名 | 最佳评分 | 最佳参数 |")
        md.append("|------|------|--------|----------|----------|")
        for i, r in enumerate(ranked, 1):
            sn = r.get("strategy_name", "")
            cn = name_map.get(sn, "—")
            bs = r.get("best_score", 0)
            bp = r.get("best_params", {})
            marker = " 🐉" if sn == V4_STRATEGY_NAME else ""
            md.append(f"| {i} | {sn} | {cn}{marker} | {bs:.4f} | `{bp}` |")
        md.append("")

    # 每个策略详情
    for r in results_by_strategy:
        sn = r.get("strategy_name", "unknown")
        cn = name_map.get(sn, sn)
        marker = " 🐉" if sn == V4_STRATEGY_NAME else ""
        md.append(f"## {cn}({sn}){marker}\n")

        if r.get("error"):
            md.append(f"**失败**: {r['error']}\n")
            continue

        best_params = r.get("best_params")
        best_score = r.get("best_score")
        if best_score is not None:
            md.append(f"- 最佳评分: {best_score:.4f}")
            md.append(f"- 最佳参数: `{best_params}`")
            md.append("")

        details = r.get("result_detail", [])
        if details:
            md.append("| 排名 | 参数 | 命中率 | 平均收益 | 最大回撤 | 选股数 | 评分 |")
            md.append("|------|------|--------|----------|----------|--------|------|")
            for d in details[:10]:
                rank = d.get("rank", "")
                params = str(d.get("params", ""))
                hit_rate = d.get("hit_rate_5d", 0)
                avg_ret = d.get("avg_return_5d", 0)
                drawdown = d.get("max_drawdown", 0)
                total_picks = d.get("total_picks", 0)
                score = d.get("score", 0)
                md.append(
                    f"| {rank} | {params} | {hit_rate:.2%} | {avg_ret:.2%} "
                    f"| {drawdown:.2%} | {total_picks} | {score:.4f} |"
                )
            md.append("")

    md.append("---\n*选股系统自动生成*\n")
    return summary_text, "\n".join(md)


def generate_v4_opt_report(
    results: list,
    elapsed: float,
    start_date: date,
    end_date: date,
    auto_applied: bool = False,
) -> tuple[str, str]:
    """生成 V4 量价配合策略参数优化报告。

    Args:
        results: list[GridSearchResult]，已按 score 降序排列
        elapsed: 耗时秒数
        start_date: 回测起始日期
        end_date: 回测结束日期
        auto_applied: 是否已自动应用最佳参数

    Returns:
        (summary_text, markdown_content)
    """
    elapsed_min = int(elapsed / 60)
    elapsed_sec = int(elapsed % 60)
    total = len(results)

    # ── 摘要文本 ──
    if results:
        best = results[0]
        m = best.metrics
        p = best.params
        apply_mark = "✅ 已自动应用" if auto_applied else "⏸ 未自动应用"
        summary_lines = [
            f"⏱ 耗时 {elapsed_min}分{elapsed_sec}秒 | 参数组合 {total} 组",
            f"🏆 最佳综合得分: {best.score:.4f}",
            f"  min_t0_pct_chg={p.get('min_t0_pct_chg')}, "
            f"washout={p.get('min_washout_days')}, "
            f"shrink={p.get('max_vol_shrink_ratio')}, "
            f"ma_tol={p.get('ma_support_tolerance')}",
            f"  5d胜率={m.win_rate_5d:.1%}, 盈亏比={m.profit_loss_ratio:.2f}, 夏普={m.sharpe_ratio:.2f}",
            f"📊 最佳参数 {apply_mark}",
        ]
        summary_text = "\n".join(summary_lines)
    else:
        summary_text = f"⚠️ V4 优化完成，但无有效结果（{total} 组均失败）"

    # ── Markdown 完整报告 ──
    md = [f"# 🐉 V4 量价配合策略 — 每周参数优化报告\n"]
    md.append(f"**回测区间：** {start_date} ~ {end_date}")
    md.append(f"**参数组合：** {total} 组 | **耗时：** {elapsed_min} 分 {elapsed_sec} 秒\n")

    if not results:
        md.append("⚠️ 无有效结果，请检查日志。\n")
        md.append("---\n*选股系统自动生成*\n")
        return summary_text, "\n".join(md)

    # Top 10
    top_n = results[:10]
    md.append("## 🏆 Top 参数组合\n")
    md.append("| 排名 | min_t0_pct_chg | min_washout | max_vol_shrink | ma_tol | 5d胜率 | 盈亏比 | 夏普 | 综合得分 |")
    md.append("|------|---------------|-------------|---------------|--------|--------|--------|------|---------|")
    for i, r in enumerate(top_n, 1):
        p = r.params
        m = r.metrics
        md.append(
            f"| {i} "
            f"| {p.get('min_t0_pct_chg')} "
            f"| {p.get('min_washout_days')} "
            f"| {p.get('max_vol_shrink_ratio')} "
            f"| {p.get('ma_support_tolerance')} "
            f"| {m.win_rate_5d:.1%} "
            f"| {m.profit_loss_ratio:.2f} "
            f"| {m.sharpe_ratio:.2f} "
            f"| {r.score:.4f} |"
        )
    md.append("")

    # 最佳参数详情
    best = results[0]
    apply_mark = "✅ 已自动应用" if auto_applied else "⏸ 未自动应用"
    md.append(f"## 📊 最佳参数（{apply_mark}）\n")
    md.append("```json")
    import json
    md.append(json.dumps(best.params, ensure_ascii=False, indent=2))
    md.append("```\n")

    # 信号统计
    bm = best.metrics
    md.append("## 📈 最佳参数信号统计\n")
    md.append("| 指标 | 值 |")
    md.append("|------|-----|")
    md.append(f"| 总信号数 | {bm.total_signals} |")
    md.append(f"| 月均信号 | {bm.signals_per_month:.1f} |")
    md.append(f"| 1日胜率 | {bm.win_rate_1d:.1%} |")
    md.append(f"| 3日胜率 | {bm.win_rate_3d:.1%} |")
    md.append(f"| 5日胜率 | {bm.win_rate_5d:.1%} |")
    md.append(f"| 10日胜率 | {bm.win_rate_10d:.1%} |")
    md.append(f"| 平均5日收益 | {bm.avg_ret_5d:.2%} |")
    md.append(f"| 盈亏比 | {bm.profit_loss_ratio:.2f} |")
    md.append(f"| 最大回撤 | {bm.max_drawdown:.2%} |")
    md.append(f"| 夏普比率 | {bm.sharpe_ratio:.2f} |")
    md.append("")

    md.append("---\n*选股系统自动生成*\n")
    return summary_text, "\n".join(md)


def generate_retry_report(
    target_date: date,
    retried: int,
    succeeded: int,
    still_failed: list[dict[str, str]],
) -> tuple[str, str]:
    """生成失败重试报告。"""
    fail_count = len(still_failed)

    summary_text = (
        f"🔄 重试 {retried} 只，成功 {succeeded} 只，仍失败 {fail_count} 只"
    )

    md = [f"# 失败重试报告 — {target_date}\n"]
    md.append("## 概况\n")
    md.append(f"- 重试总数: {retried}")
    md.append(f"- 成功: {succeeded}")
    md.append(f"- 仍失败: {fail_count}")
    md.append("")

    if still_failed:
        md.append("## 失败明细\n")
        md.append("| 代码 | 错误原因 |")
        md.append("|------|----------|")
        for item in still_failed:
            md.append(f"| {item['ts_code']} | {item.get('error', 'unknown')} |")
        md.append("")

    md.append("---\n*选股系统自动生成*\n")
    return summary_text, "\n".join(md)
