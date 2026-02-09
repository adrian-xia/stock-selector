#!/bin/bash
# A股智能选股系统 - 生产环境启动脚本

set -e

# 切换到项目目录
cd /Users/adrian/Developer/Codes/stock-selector

# 加载生产环境变量
if [ -f .env.prod ]; then
    export $(cat .env.prod | grep -v '^#' | xargs)
fi

# 启动服务
exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
