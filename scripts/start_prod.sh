#!/bin/bash
# A股智能选股系统 - 生产环境启动脚本（前端 + 后端）

set -e

# 切换到项目目录
cd /Users/adrian/Developer/Codes/stock-selector

# 加载生产环境变量（过滤注释和空行）
if [ -f .env.prod ]; then
    set -a
    source <(cat .env.prod | grep -v '^#' | grep -v '^$' | sed 's/#.*$//')
    set +a
fi

# 日志目录
LOG_DIR="$HOME/Library/Logs"
mkdir -p "$LOG_DIR"

# 启动前端（后台）
echo "启动前端服务..."
cd web
/Users/adrian/.nvm/versions/node/v24.13.0/bin/pnpm dev > "$LOG_DIR/stock-selector-frontend.log" 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > /tmp/stock-selector-frontend.pid
echo "前端已启动 (PID: $FRONTEND_PID, 端口: 5173)"

# 返回项目根目录
cd ..

# 启动后端（前台，使用 exec）
echo "启动后端服务..."
exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
