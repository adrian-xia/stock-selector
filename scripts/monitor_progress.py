#!/usr/bin/env python3
"""同步进度监控脚本。

查询数据库各表记录数，读取最新日志，输出格式化进度报告。
"""

import asyncio
import sys
from datetime import datetime, timezone, timedelta

from sqlalchemy import text

# 确保能 import app 模块
sys.path.insert(0, ".")

TZ_CST = timezone(timedelta(hours=8))

# P0 raw 表
P0_TABLES = [
    ("raw_tushare_daily", "日线行情"),
    ("raw_tushare_adj_factor", "复权因子"),
    ("raw_tushare_daily_basic", "每日指标"),
]

# P1 raw 表
P1_TABLES = [
    ("raw_tushare_fina_indicator", "财务指标"),
]

# P2 raw 表
P2_TABLES = [
    ("raw_tushare_moneyflow", "资金流向"),
    ("raw_tushare_top_list", "龙虎榜明细"),
    ("raw_tushare_top_inst", "龙虎榜机构"),
]

# P3 raw 表
P3_TABLES = [
    ("raw_tushare_index_daily", "指数日线"),
    ("raw_tushare_index_weight", "指数权重"),
    ("raw_tushare_index_factor_pro", "指数技术因子"),
    ("raw_tushare_index_basic", "指数基础信息"),
    ("raw_tushare_index_classify", "行业分类"),
    ("raw_tushare_index_member_all", "行业成分股"),
]

# P4 raw 表
P4_TABLES = [
    ("raw_tushare_ths_index", "同花顺板块"),
    ("raw_tushare_ths_daily", "同花顺板块日线"),
    ("raw_tushare_ths_member", "同花顺板块成分"),
    ("raw_tushare_dc_index", "东财板块"),
    ("raw_tushare_dc_member", "东财板块成分"),
    ("raw_tushare_tdx_index", "通达信板块"),
    ("raw_tushare_tdx_daily", "通达信板块日线"),
    ("raw_tushare_tdx_member", "通达信板块成分"),
]

# P5 raw 表（全部）
P5_TABLES = [
    # 日频核心
    ("raw_tushare_suspend_d", "停复牌"),
    ("raw_tushare_limit_list_d", "涨跌停统计"),
    ("raw_tushare_margin", "融资融券汇总"),
    ("raw_tushare_margin_detail", "融资融券明细"),
    ("raw_tushare_block_trade", "大宗交易"),
    ("raw_tushare_daily_share", "每日股本"),
    ("raw_tushare_stk_factor", "技术因子"),
    ("raw_tushare_stk_factor_pro", "技术因子Pro"),
    ("raw_tushare_hm_board", "热门板块"),
    ("raw_tushare_hm_list", "热门股票"),
    ("raw_tushare_ths_hot", "同花顺热股"),
    ("raw_tushare_dc_hot", "东财热股"),
    ("raw_tushare_ths_limit", "同花顺涨跌停"),
    # 日频补充
    ("raw_tushare_hsgt_top10", "沪深港通十大"),
    ("raw_tushare_ggt_daily", "港股通每日"),
    ("raw_tushare_ccass_hold", "港股通持股汇总"),
    ("raw_tushare_ccass_hold_detail", "港股通持股明细"),
    ("raw_tushare_hk_hold", "沪深港通持股"),
    ("raw_tushare_cyq_perf", "筹码分布"),
    ("raw_tushare_cyq_chips", "筹码集中度"),
    ("raw_tushare_slb_len", "转融通借入"),
    ("raw_tushare_limit_step", "涨跌停阶梯"),
    ("raw_tushare_hm_detail", "热门股票明细"),
    ("raw_tushare_stk_auction", "集合竞价"),
    ("raw_tushare_stk_auction_o", "集合竞价(开盘)"),
    ("raw_tushare_kpl_list", "开盘啦涨跌停"),
    ("raw_tushare_kpl_concept", "开盘啦概念"),
    ("raw_tushare_broker_recommend", "券商推荐"),
    # 周频/月频
    ("raw_tushare_weekly", "周线行情"),
    ("raw_tushare_monthly", "月线行情"),
    ("raw_tushare_ggt_monthly", "港股通月度"),
    # 季度
    ("raw_tushare_top10_holders", "前十大股东"),
    ("raw_tushare_top10_floatholders", "前十大流通股东"),
    ("raw_tushare_stk_holdernumber", "股东户数"),
    ("raw_tushare_stk_holdertrade", "股东增减持"),
    # 静态
    ("raw_tushare_stock_company", "上市公司信息"),
    ("raw_tushare_margin_target", "融资融券标的"),
    ("raw_tushare_namechange", "股票曾用名"),
    ("raw_tushare_stk_managers", "管理层"),
    ("raw_tushare_stk_rewards", "管理层薪酬"),
    ("raw_tushare_new_share", "IPO新股"),
    ("raw_tushare_stk_list_his", "上市历史"),
    ("raw_tushare_pledge_stat", "股权质押统计"),
    ("raw_tushare_pledge_detail", "股权质押明细"),
    ("raw_tushare_repurchase", "股票回购"),
    ("raw_tushare_share_float", "限售股解禁"),
    ("raw_tushare_report_rc", "券商月度金股"),
    ("raw_tushare_stk_surv", "机构调研"),
]

# 业务表
BIZ_TABLES = [
    ("stocks", "股票列表"),
    ("trade_calendar", "交易日历"),
    ("stock_daily", "日线行情"),
    ("finance_indicator", "财务指标"),
    ("money_flow", "资金流向"),
    ("dragon_tiger", "龙虎榜"),
    ("index_daily", "指数日线"),
    ("index_weight", "指数权重"),
    ("index_technical_daily", "指数技术因子"),
    ("technical_daily", "技术指标"),
    ("suspend_info", "停复牌"),
    ("limit_list_daily", "涨跌停"),
    ("concept_index", "板块指数"),
    ("concept_daily", "板块日线"),
    ("concept_member", "板块成分股"),
    ("concept_technical_daily", "板块技术因子"),
]

async def get_table_count(session, table_name: str) -> int:
    """安全获取表记录数，表不存在返回 -1。"""
    try:
        result = await session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        return result.scalar()
    except Exception:
        await session.rollback()
        return -1


async def get_latest_trade_date(session, table_name: str) -> str:
    """获取 raw 表中最新的 trade_date。"""
    try:
        result = await session.execute(
            text(f"SELECT MAX(trade_date) FROM {table_name}")
        )
        val = result.scalar()
        return str(val) if val else "-"
    except Exception:
        await session.rollback()
        return "-"


async def get_sync_progress(session) -> dict:
    """从 raw_sync_progress 表获取同步进度。"""
    try:
        result = await session.execute(
            text("SELECT table_name, last_sync_date, last_sync_rows FROM raw_sync_progress ORDER BY table_name")
        )
        return {row[0]: {"date": row[1], "rows": row[2]} for row in result.all()}
    except Exception:
        await session.rollback()
        return {}


import unicodedata


def _display_width(s: str) -> int:
    """计算字符串的终端显示宽度（CJK 字符占 2 列）。"""
    w = 0
    for ch in s:
        if unicodedata.east_asian_width(ch) in ("W", "F"):
            w += 2
        else:
            w += 1
    return w


def _pad(s: str, width: int, align: str = "left") -> str:
    """按显示宽度填充字符串。"""
    dw = _display_width(s)
    pad = max(0, width - dw)
    if align == "right":
        return " " * pad + s
    return s + " " * pad


def fmt_num(n: int) -> str:
    """格式化数字，加千分位。"""
    if n < 0:
        return "N/A"
    return f"{n:,}"


def status_icon(count: int) -> str:
    if count < 0:
        return "⚠ 不存在"
    if count == 0:
        return "待同步"
    return "✓"


def print_report(raw_counts: dict, biz_counts: dict, latest_dates: dict, sync_progress: dict):
    """输出格式化进度报告。"""
    now = datetime.now(TZ_CST).strftime("%Y-%m-%d %H:%M")
    print()
    print(f"  ⏺ 同步进度报告 — {now}")
    print()

    # --- Raw 表进度 ---
    print("  ┌──────────────────────────────────┬──────────┬─────────────┬──────────────┐")
    print(f"  │ {_pad('Raw 表', 32)} │ {_pad('状态', 8)} │ {_pad('记录数', 11, 'right')} │ {_pad('最新日期', 12, 'right')} │")
    print("  ├──────────────────────────────────┼──────────┼─────────────┼──────────────┤")

    all_groups = [
        ("P0", P0_TABLES),
        ("P1", P1_TABLES),
        ("P2", P2_TABLES),
        ("P3", P3_TABLES),
        ("P4", P4_TABLES),
        ("P5", P5_TABLES),
    ]
    for group_name, tables in all_groups:
        print(f"  │ {_pad(group_name, 32)} │          │             │              │")
        for tbl, label in tables:
            cnt = raw_counts.get(tbl, -1)
            icon = status_icon(cnt)
            ld = latest_dates.get(tbl, "-")
            print(f"  │   {_pad(label, 30)} │ {_pad(icon, 8)} │ {_pad(fmt_num(cnt), 11, 'right')} │ {_pad(ld, 12, 'right')} │")

    print("  └──────────────────────────────────┴──────────┴─────────────┴──────────────┘")
    print()

    # --- 业务表统计 ---
    print("  ┌──────────────────────────────────┬──────────┬─────────────┐")
    print(f"  │ {_pad('业务表', 32)} │ {_pad('状态', 8)} │ {_pad('记录数', 11, 'right')} │")
    print("  ├──────────────────────────────────┼──────────┼─────────────┤")
    for tbl, label in BIZ_TABLES:
        cnt = biz_counts.get(tbl, -1)
        icon = status_icon(cnt)
        print(f"  │ {_pad(label, 32)} │ {_pad(icon, 8)} │ {_pad(fmt_num(cnt), 11, 'right')} │")
    print("  └──────────────────────────────────┴──────────┴─────────────┘")
    print()

    # --- sync_progress 摘要 ---
    if sync_progress:
        synced = sum(1 for v in sync_progress.values() if v["rows"] and v["rows"] > 0)
        print(f"  raw_sync_progress: {synced}/{len(sync_progress)} 张表有记录")
    print()


async def check_progress():
    """执行一次进度检查。"""
    from app.config import settings  # noqa: F401 — 触发 .env 加载
    from app.database import async_session_factory

    async with async_session_factory() as session:
        # 收集所有 raw 表记录数
        all_raw = P0_TABLES + P1_TABLES + P2_TABLES + P3_TABLES + P4_TABLES + P5_TABLES
        raw_counts = {}
        latest_dates = {}
        for tbl, _ in all_raw:
            raw_counts[tbl] = await get_table_count(session, tbl)
            latest_dates[tbl] = await get_latest_trade_date(session, tbl)

        # 收集业务表记录数
        biz_counts = {}
        for tbl, _ in BIZ_TABLES:
            biz_counts[tbl] = await get_table_count(session, tbl)

        # 同步进度
        sync_progress = await get_sync_progress(session)

    print_report(raw_counts, biz_counts, latest_dates, sync_progress)


async def main():
    """主函数：单次检查或循环监控。"""
    loop = "--loop" in sys.argv
    await check_progress()
    if loop:
        while True:
            await asyncio.sleep(30 * 60)  # 30 分钟
            await check_progress()


if __name__ == "__main__":
    asyncio.run(main())
