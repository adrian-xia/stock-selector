#!/bin/bash
# 同步监控脚本（每 30 分钟检查一次）
# 使用方式：bash scripts/sync_monitor.sh
#
# 监控内容：
#   - 同步进程是否存活
#   - 批次完成进度
#   - 最近日志输出
#   - 数据库表记录数

set -uo pipefail

export APP_ENV_FILE=.env.prod
LOGFILE="logs/full_sync.log"
PROGRESS_FILE="logs/sync_progress.txt"
INTERVAL=1800  # 30 分钟

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

check_status() {
    log "========== 同步状态检查 =========="

    # 1. 检查进程是否存活
    if pgrep -f "full_sync.sh" > /dev/null 2>&1; then
        log "✓ 同步进程运行中"
    else
        log "✗ 同步进程未运行"
    fi

    # 2. 批次进度
    log "--- 批次进度 ---"
    if [ -f "$PROGRESS_FILE" ]; then
        cat "$PROGRESS_FILE"
    else
        log "尚未开始"
    fi

    # 3. 最近 20 行日志
    log "--- 最近日志 ---"
    if [ -f "$LOGFILE" ]; then
        tail -20 "$LOGFILE"
    else
        log "日志文件不存在"
    fi

    # 4. 数据库记录数
    log "--- 数据库统计 ---"
    uv run python -c "
import asyncio
from sqlalchemy import text
from app.database import async_session_factory

async def check():
    tables = [
        'stocks', 'stock_daily', 'technical_daily',
        'raw_tushare_fina_indicator', 'raw_tushare_moneyflow',
        'index_daily', 'concept_index', 'concept_daily',
    ]
    async with async_session_factory() as s:
        for t in tables:
            try:
                r = await s.execute(text(f'SELECT COUNT(*) FROM {t}'))
                print(f'  {t}: {r.scalar():,} 行')
            except Exception:
                print(f'  {t}: 表不存在或查询失败')

asyncio.run(check())
" 2>/dev/null || log "数据库查询失败"

    log "=================================="
    echo
}

log "同步监控启动，每 30 分钟检查一次（Ctrl+C 退出）"
echo

while true; do
    check_status
    sleep $INTERVAL
done
