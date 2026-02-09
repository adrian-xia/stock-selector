#!/bin/bash
# A股智能选股系统 - 服务管理脚本（macOS launchd）

SERVICE_NAME="com.stock-selector"
PLIST_FILE="$HOME/Library/LaunchAgents/${SERVICE_NAME}.plist"
LOG_FILE="$HOME/Library/Logs/stock-selector.log"
ERROR_LOG_FILE="$HOME/Library/Logs/stock-selector.error.log"

case "$1" in
    start)
        echo "启动 stock-selector 服务..."
        launchctl load "$PLIST_FILE" 2>/dev/null || launchctl start "$SERVICE_NAME"
        sleep 2
        if launchctl list | grep -q "$SERVICE_NAME"; then
            echo "✓ 服务已启动"
            echo "查看日志：tail -f $LOG_FILE"
        else
            echo "✗ 服务启动失败"
            exit 1
        fi
        ;;

    stop)
        echo "停止 stock-selector 服务..."
        launchctl stop "$SERVICE_NAME" 2>/dev/null
        launchctl unload "$PLIST_FILE" 2>/dev/null
        echo "✓ 服务已停止"
        ;;

    restart)
        echo "重启 stock-selector 服务..."
        $0 stop
        sleep 2
        $0 start
        ;;

    status)
        echo "检查 stock-selector 服务状态..."
        if launchctl list | grep -q "$SERVICE_NAME"; then
            echo "✓ 服务正在运行"
            launchctl list | grep "$SERVICE_NAME"
            echo ""
            echo "最近日志："
            tail -10 "$LOG_FILE"
        else
            echo "✗ 服务未运行"
        fi
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
