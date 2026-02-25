import asyncio, subprocess
from datetime import datetime
from sqlalchemy import text

async def report():
    from app.database import async_session_factory
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    async with async_session_factory() as s:
        async def cnt(t):
            try:
                r = await s.execute(text(f'SELECT COUNT(*) FROM {t}'))
                return r.scalar() or 0
            except:
                return -1
        d = {}
        for t in ['stocks','stock_daily','trade_calendar','raw_tushare_daily','raw_tushare_adj_factor',
            'raw_tushare_daily_basic','raw_tushare_moneyflow','raw_tushare_top_list','raw_tushare_top_inst',
            'raw_tushare_moneyflow_hsgt','raw_tushare_moneyflow_dc','raw_tushare_moneyflow_ths',
            'raw_tushare_moneyflow_ind_ths','raw_tushare_moneyflow_cnt_ths','raw_tushare_moneyflow_ind_dc',
            'raw_tushare_moneyflow_mkt_dc','money_flow','dragon_tiger',
            'raw_tushare_index_daily','raw_tushare_index_weight','raw_tushare_index_factor_pro',
            'index_daily','index_weight','index_technical_daily',
            'raw_tushare_ths_index','raw_tushare_ths_daily','raw_tushare_ths_member',
            'concept_index','concept_daily','concept_member','concept_technical_daily',
            'suspend_info','limit_list_daily','technical_daily','finance_indicator']:
            d[t] = await cnt(t)
    p = subprocess.run(['grep','-c','sync_concept_daily.*完成','/Users/adrian/Developer/Codes/stock-selector/logs/batch23_sync.log'],capture_output=True,text=True)
    p4 = int(p.stdout.strip()) if p.returncode==0 else 0
    def v(x): return f'{x:>13,}' if x>=0 else '          N/A'
    def st(x): return '✓' if x>0 else ('❌' if x<0 else '待同步')
    if d.get('concept_member',0)>0: cur='P4 板块成分股同步中'
    elif p4>0 and p4<4891: cur=f'P4 板块日线同步中 ({p4}/4891)'
    elif p4>=4891: cur='P4 完成，进入成分股'
    else: cur='确认中...'
    p2o=sum(1 for x in ['moneyflow_dc','moneyflow_ths','moneyflow_ind_ths','moneyflow_cnt_ths','moneyflow_ind_dc','moneyflow_mkt_dc'] if d.get(f'raw_tushare_{x}',0)>0)
    print(f'同步进度报告 — {now}')
    print(f'\n┌──────────────────────────┬──────────┬──────────────────────────────────────┐')
    print(f'│ 数据项                   │ 状态     │ 详情                                 │')
    print(f'├──────────────────────────┼──────────┼──────────────────────────────────────┤')
    print(f'│ 批次 1 (已完成)          │          │                                      │')
    print(f'├──────────────────────────┼──────────┼──────────────────────────────────────┤')
    print(f'│ P0 日线                  │ ✓ 完成   │ 4891/4891 天                         │')
    print(f'│ P1 财务                  │ ✗ 全失败 │ 80 季全部字段精度溢出                 │')
    print(f'│ P3 index_daily           │ ✓ 完成   │ {v(d["raw_tushare_index_daily"])} 条 │')
    print(f'│ P3 index_weight          │ ✓ 完成   │ {v(d["raw_tushare_index_weight"])} 条 │')
    print(f'│ P3 idx_factor_pro        │ 部分完成 │ {v(d["raw_tushare_index_factor_pro"])} 条 │')
    print(f'│ 技术指标                 │ ✗ 未执行 │                                      │')
    print(f'├──────────────────────────┼──────────┼──────────────────────────────────────┤')
    print(f'│ 批次 2 (进行中)          │          │ {cur:<36} │')
    print(f'├──────────────────────────┼──────────┼──────────────────────────────────────┤')
    print(f'│ P2 moneyflow             │ ✓ 完成   │ {v(d["raw_tushare_moneyflow"])} 条 │')
    print(f'│ P2 top_list              │ ✓ 完成   │ {v(d["raw_tushare_top_list"])} 条 │')
    print(f'│ P2 top_inst              │ ✓ 完成   │ {v(d["raw_tushare_top_inst"])} 条 │')
    print(f'│ P2 moneyflow_hsgt        │ {st(d["raw_tushare_moneyflow_hsgt"]):<8} │ {v(d["raw_tushare_moneyflow_hsgt"])} 条 │')
    print(f'│ P2 其余 6 张             │ {p2o}/6完成 │                                      │')
    print(f'│ P4 concept_index         │ {st(d["concept_index"]):<8} │ {v(d["concept_index"])} 条 │')
    print(f'│ P4 concept_daily         │ {st(d["concept_daily"]):<8} │ {v(d["concept_daily"])} 条 ({p4}/4891天) │')
    print(f'│ P4 concept_member        │ {st(d["concept_member"]):<8} │ {v(d["concept_member"])} 条 │')
    print(f'├──────────────────────────┼──────────┼──────────────────────────────────────┤')
    print(f'│ 批次 3 (待执行)          │          │                                      │')
    print(f'├──────────────────────────┼──────────┼──────────────────────────────────────┤')
    print(f'│ P5 suspend_info          │ {st(d["suspend_info"]):<8} │ {v(d["suspend_info"])} 条 │')
    print(f'│ P5 limit_list_daily      │ {st(d["limit_list_daily"]):<8} │ {v(d["limit_list_daily"])} 条 │')
    print(f'│ P5 (其余 46 张)          │ 待同步   │                                      │')
    print(f'└──────────────────────────┴──────────┴──────────────────────────────────────┘')
    print(f'\n数据库关键业务表统计：\n')
    print(f'┌──────────────────────────────────────┬─────────────────┬────────┐')
    print(f'│ 表                                   │       记录数    │ 状态   │')
    print(f'├──────────────────────────────────────┼─────────────────┼────────┤')
    for t,desc in [('stocks','股票列表'),('stock_daily','日线行情'),('trade_calendar','交易日历'),
        ('finance_indicator','财务指标'),('money_flow','资金流向'),('dragon_tiger','龙虎榜'),
        ('index_daily','指数日线'),('index_weight','指数权重'),('index_technical_daily','指数技术'),
        ('concept_index','板块列表'),('concept_daily','板块日线'),('concept_member','板块成分'),
        ('suspend_info','停复牌'),('limit_list_daily','涨跌停'),('technical_daily','技术指标')]:
        x=d.get(t,-1)
        print(f'│ {t:<36} │ {v(x):>15} │ {st(x):<6} │')
    print(f'└──────────────────────────────────────┴─────────────────┴────────┘')

asyncio.run(report())
