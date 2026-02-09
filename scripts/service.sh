#!/bin/bash
# A股智能选股系统 - 服务管理脚本（macOS launchd）

SERVICE_NAME="com.stock-selector"
PLIST_FILE="$HOME/Library/LaunchAgents/${SERVICE_NAME}.plist"
LOG_FILE="$HOME/Library/Logs/stock-selector.log"
ERROR_LOG_FILE="$HOME/Library/Logs/stock-selector.error.log"
FRONTEND_LOG_FILE="$HOME/Library/Logs/stock-selector-frontend.log"
FRONTEND_PID_FILE="/tmp/stock-selector-frontend.pid"

# 停止前端进程
stop_frontend() {
    if [ -f "$FRONTEND_PID_FILE" ]; then
        FRONTEND_PID=$(cat "$FRONTEND_PID_FILE")
        if ps -p "$FRONTEND_PID" > /dev/null 2>&1; then
            echo "停止前端服务 (PID: $FRONTEND_PID)..."
            kill "$FRONTEND_PID" 2>/dev/null
            rm -f "$FRONTEND_PID_FILE"
        fi
    fi
    # 额外清理：查找并停止所有 vite 进程
    pkill -f "vite.*web" 2>/dev/null || true
}

case "$1" in
    start)
        echo "启动 stock-selector 服务（前端 + 后端）..."
        launchctl load "$PLIST_FILE" 2>/dev/null || launchctl start "$SERVICE_NAME"
        sleep 3

        # 检查后端
        BACKEND_OK=false
        if launchctl list | grep -q "$SERVICE_NAME"; then
            echo "✓ 后端已启动 (http://localhost:8000)"
            BACKEND_OK=true
        else
            echo "✗ 后端启动失败"
        fi

        # 检查前端
        FRONTEND_OK=false
        if [ -f "$FRONTEND_PID_FILE" ]; then
            FRONTEND_PID=$(cat "$FRONTEND_PID_FILE")
            if ps -p "$FRONTEND_PID" > /dev/null 2>&1; then
                echo "✓ 前端已启动 (http://localhost:5173, PID: $FRONTEND_PID)"
                FRONTEND_OK=true
            fi
        fi

        if [ "$BACKEND_OK" = false ] || [ "$FRONTEND_OK" = false ]; then
            echo ""
            echo "部分服务启动失败，请查看日志："
            echo "  后端日志: tail -f $LOG_FILE"
            echo "  前端日志: tail -f $FRONTEND_LOG_FILE"
            exit 1
        fi

        echo ""
        echo "所有服务已启动！"
        echo "  前端: http://localhost:5173"
        echo "  后端: http://localhost:8000"
        echo "  API 文档: http://localhost:8000/docs"
        ;;

    stop)
        echo "停止 stock-selector 服务（前端 + 后端）..."

        # 停止前端
        stop_frontend

        # 停止后端
        launchctl stop "$SERVICE_NAME" 2>/dev/null
        launchctl unload "$PLIST_FILE" 2>/dev/null

        echo "✓ 所有服务已停止"
        ;;

    restart)
        echo "重启 stock-selector 服务（前端 + 后端）..."
        $0 stop
        sleep 2
        $0 start
        ;;

    status)
        echo "检查 stock-selector 服务状态..."
        echo ""

        # 检查后端
        echo "【后端服务】"
        if launchctl list | grep -q "$SERVICE_NAME"; then
            echo "✓ 运行中 (http://localhost:8000)"
            launchctl list | grep "$SERVICE_NAME"
        else
            echo "✗ 未运行"
        fi

        echo ""
        echo "【前端服务】"
        # 检查前端
        if [ -f "$FRONTEND_PID_FILE" ]; then
            FRONTEND_PID=$(cat "$FRONTEND_PID_FILE")
            if ps -p "$FRONTEND_PID" > /dev/null 2>&1; then
                echo "✓ 运行中 (http://localhost:5173, PID: $FRONTEND_PID)"
            else
                echo "✗ 未运行 (PID 文件存在但进程不存在)"
            fi
        else
            echo "✗ 未运行"
        fi

        echo ""
        echo "【最近日志】"
        echo "后端："
        tail -5 "$LOG_FILE" 2>/dev/null || echo "  无日志"
        echo ""
        echo "前端："
        tail -5 "$FRONTEND_LOG_FILE" 2>/dev/null || echo "  无日志"
        ;;

    logs)
        echo "查看实时日志（Ctrl+C 退出）..."
        tail -f "$LOG_FILE"
        ;;

    errors)
        echo "查看错误日志（Ctrl+C 退出）..."
        tail -f "$ERROR_LOG_FILE"
        ;;

    install)
        echo "安装 stock-selector 服务..."
        if [ ! -f "$PLIST_FILE" ]; then
            echo "✗ plist 文件不存在：$PLIST_FILE"
            exit 1
        fi
        launchctl load "$PLIST_FILE"
        echo "✓ 服务已安装并启动"
        echo "服务将在登录时自动启动"
        ;;

    uninstall)
        echo "卸载 stock-selector 服务..."
        launchctl unload "$PLIST_FILE" 2>/dev/null
        echo "✓ 服务已卸载"
        echo "plist 文件仍保留在：$PLIST_FILE"
        ;;

    *)
        echo "A股智能选股系统 - 服务管理"
        echo ""
        echo "用法: $0 {start|stop|restart|status|logs|errors|install|uninstall}"
        echo ""
        echo "命令说明："
        echo "  start      - 启动服务"
        echo "  stop       - 停止服务"
        echo "  restart    - 重启服务"
        echo "  status     - 查看服务状态"
        echo "  logs       - 查看实时日志"
        echo "  errors     - 查看错误日志"
        echo "  install    - 安装服务（开机自启）"
        echo "  uninstall  - 卸载服务"
        echo ""
        echo "日志文件："
        echo "  标准输出: $LOG_FILE"
        echo "  错误输出: $ERROR_LOG_FILE"
        exit 1
        ;;
esac
