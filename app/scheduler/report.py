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


def generate_post_market_report(
    target_date: date,
    elapsed: float,
    summary: dict[str, Any],
    picks: list[Any],
    plans: list[dict[str, Any]],
) -> tuple[str, str]:
    """生成盘后链路报告。

    Args:
        target_date: 目标交易日
        elapsed: 总耗时（秒）
        summary: get_sync_summary() 返回的摘要
        picks: StockPick 列表
        plans: 交易计划 dict 列表

    Returns:
        (摘要文本, Markdown 完整报告)
    """
    elapsed_min = int(elapsed / 60)
    elapsed_sec = int(elapsed % 60)
    pick_count = len(picks) if picks else 0
    plan_count = len(plans) if plans else 0

    # ── 摘要文本（3 行） ──
    summary_lines = [
        f"⏱ 耗时 {elapsed_min}分{elapsed_sec}秒 | 同步 {summary.get('data_done', 'N/A')} 只",
        f"🎯 选股 {pick_count} 条 | 交易计划 {plan_count} 条",
        f"📈 完成率 {summary.get('completion_rate', 0) * 100:.1f}%",
    ]
    summary_text = "\n".join(summary_lines)

    # ── Markdown 完整报告 ──
    md = [f"# 盘后分析报告 — {target_date}\n"]

    # 执行概况表格
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

    # 策略分布表格
    if picks:
        strategy_counter: Counter[str] = Counter()
        for p in picks:
            for s in p.matched_strategies:
                strategy_counter[s] += 1

        md.append(f"## 策略分布（{len(strategy_counter)} 个策略命中）\n")
        md.append("| 策略 | 命中数 |")
        md.append("|------|--------|")
        for sname, cnt in strategy_counter.most_common():
            md.append(f"| {sname} | {cnt} |")
        md.append("")

    # 涨跌分布统计
    if picks:
        up_count = sum(1 for p in picks if p.pct_chg > 0)
        down_count = sum(1 for p in picks if p.pct_chg < 0)
        flat_count = sum(1 for p in picks if p.pct_chg == 0)
        avg_chg = sum(p.pct_chg for p in picks) / len(picks)

        md.append("## 涨跌分布\n")
        md.append("| 指标 | 值 |")
        md.append("|------|-----|")
        md.append(f"| 上涨 | {up_count} |")
        md.append(f"| 下跌 | {down_count} |")
        md.append(f"| 平盘 | {flat_count} |")
        md.append(f"| 平均涨跌幅 | {avg_chg:+.2f}% |")
        md.append("")

    # 选股明细完整表格（全部 picks，不截断）
    if picks:
        md.append(f"## 选股明细（共 {pick_count} 条）\n")
        md.append("| 排名 | 代码 | 名称 | 收盘 | 涨跌幅 | 加权得分 | 策略 |")
        md.append("|------|------|------|------|--------|----------|------|")
        for i, p in enumerate(picks, 1):
            name = getattr(p, "name", "") or p.ts_code
            chg_str = f"{p.pct_chg:+.2f}%" if p.pct_chg else "0.00%"
            strats = ", ".join(p.matched_strategies)
            md.append(
                f"| {i} | {p.ts_code} | {name} | {p.close} | {chg_str} "
                f"| {p.weighted_score:.2f} | {strats} |"
            )
        md.append("")

    # 交易计划表格
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
            strategy = pl.get("source_strategy", "")
            md.append(f"| {i} | {code} | {trigger} | {tp} | {sl} | {tkp} | {strategy} |")
        md.append("")

    md.append("---\n*选股系统自动生成*\n")
    markdown_content = "\n".join(md)

    return summary_text, markdown_content


def generate_market_opt_report(
    results_by_strategy: list[dict[str, Any]],
) -> tuple[str, str]:
    """生成全市场参数优化报告。

    Args:
        results_by_strategy: 每个策略的优化结果列表，每项包含：
            - strategy_name: 策略名
            - best_score: 最佳评分（可能为 None）
            - best_params: 最佳参数
            - result_detail: Top N 结果列表
            - error: 错误信息（如果失败）

    Returns:
        (摘要文本, Markdown 完整报告)
    """
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

    for r in results_by_strategy:
        name = r.get("strategy_name", "unknown")
        md.append(f"## {name}\n")

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
    markdown_content = "\n".join(md)

    return summary_text, markdown_content


def generate_retry_report(
    target_date: date,
    retried: int,
    succeeded: int,
    still_failed: list[dict[str, str]],
) -> tuple[str, str]:
    """生成失败重试报告。

    Args:
        target_date: 目标日期
        retried: 重试总数
        succeeded: 成功数
        still_failed: 仍然失败的股票列表，每项含 ts_code 和 error

    Returns:
        (摘要文本, Markdown 完整报告)
    """
    fail_count = len(still_failed)

    # ── 摘要文本 ──
    summary_text = (
        f"🔄 重试 {retried} 只，成功 {succeeded} 只，仍失败 {fail_count} 只"
    )

    # ── Markdown 完整报告 ──
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
    markdown_content = "\n".join(md)

    return summary_text, markdown_content
