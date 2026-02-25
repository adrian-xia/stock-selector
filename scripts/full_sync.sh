#!/bin/bash
# 全量数据同步脚本（分批执行 + 30 分钟监控）
# 使用方式：nohup bash scripts/full_sync.sh > logs/full_sync.log 2>&1 &
#
# 分批策略：
#   批次 1: 步骤 1-4（股票列表 + 交易日历 + P0 日线 + P1 财务 + P3 指数 + 技术指标）
#   批次 2: P2 资金流向 + P4 板块数据
#   批次 3: P5 扩展数据
#
# 每批之间自动记录完成状态，失败可从断点继续。

set -euo pipefail

export APP_ENV_FILE=.env.prod
LOGDIR="logs"
PROGRESS_FILE="$LOGDIR/sync_progress.txt"
START_DATE="2006-01-01"

mkdir -p "$LOGDIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# 检查某批次是否已完成
is_done() {
    grep -q "^$1=done$" "$PROGRESS_FILE" 2>/dev/null
}

# 标记批次完成
mark_done() {
    echo "$1=done" >> "$PROGRESS_FILE"
}

log "=========================================="
log "全量数据同步开始"
log "开始日期：$START_DATE"
log "配置文件：$APP_ENV_FILE"
log "=========================================="

# ========== 批次 1：核心数据 ==========
if ! is_done "batch1"; then
    log "[批次 1/3] 核心数据：股票列表 + 交易日历 + P0 日线 + P1 财务 + P3 指数 + 技术指标"
    uv run python -m app.data.cli init-tushare \
        --start "$START_DATE" \
        --skip-p2 --skip-concept --skip-p5
    mark_done "batch1"
    log "[批次 1/3] 完成"
else
    log "[批次 1/3] 已完成，跳过"
fi

# ========== 批次 2：资金流向 + 板块 ==========
if ! is_done "batch2"; then
    log "[批次 2/3] 资金流向（P2）+ 板块数据（P4）"
    uv run python -m app.data.cli init-tushare \
        --start "$START_DATE" \
        --skip-fina --skip-index --skip-p5
    mark_done "batch2"
    log "[批次 2/3] 完成"
else
    log "[批次 2/3] 已完成，跳过"
fi

# ========== 批次 3：扩展数据 ==========
if ! is_done "batch3"; then
    log "[批次 3/3] 扩展数据（P5）"
    uv run python -m app.data.cli init-tushare \
        --start "$START_DATE" \
        --skip-fina --skip-p2 --skip-index --skip-concept
    mark_done "batch3"
    log "[批次 3/3] 完成"
else
    log "[批次 3/3] 已完成，跳过"
fi

log "=========================================="
log "全量数据同步全部完成"
log "=========================================="
