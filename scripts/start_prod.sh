#!/bin/bash
# A股智能选股系统 - 生产环境启动脚本

set -e

# 切换到项目目录
cd /Users/adrian/Developer/Codes/stock-selector

# 加载生产环境变量（过滤注释和空行）
if [ -f .env.prod ]; then
    set -a
    source <(cat .env.prod | grep -v '^#' | grep -v '^$' | sed 's/#.*$//')
    set +a
fi

# 启动服务
exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
