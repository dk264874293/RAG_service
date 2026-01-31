#!/bin/bash

# RAG服务停止脚本
# Author: 汪培良
# Date: 2026-01-29

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目路径
PROJECT_DIR="/Users/wangpeiliang/Desktop/AI/RAG_service"
cd "$PROJECT_DIR"

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 通过PID文件停止服务
stop_by_pid() {
    if [ -f "logs/server.pid" ]; then
        PID=$(cat logs/server.pid)
        if ps -p $PID > /dev/null 2>&1; then
            log_info "通过PID文件停止服务 (PID: $PID)..."
            kill $PID
            sleep 2
            if ps -p $PID > /dev/null 2>&1; then
                log_warn "服务未响应，强制停止..."
                kill -9 $PID
            fi
            rm -f logs/server.pid
            log_info "✅ 服务已停止"
        else
            log_warn "PID文件存在但进程不运行，清理PID文件"
            rm -f logs/server.pid
        fi
    else
        log_warn "未找到PID文件"
    fi
}

# 通过端口停止服务
stop_by_port() {
    log_info "检查端口8000..."
    if lsof -Pi :8000 -sTCP:LISTEN -t > /dev/null 2>&1; then
        log_info "发现端口8000被占用，停止相关进程..."
        PIDS=$(lsof -ti:8000)
        for PID in $PIDS; do
            log_info "停止进程 $PID"
            kill $PID 2>/dev/null || kill -9 $PID 2>/dev/null || true
        done
        sleep 1
        log_info "✅ 端口8000已释放"
    else
        log_info "端口8000未被占用"
    fi
}

# 主函数
main() {
    MODE=${1:-auto}
    
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}    RAG服务停止脚本${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    
    case $MODE in
        auto)
            stop_by_pid
            stop_by_port
            ;;
        pid)
            stop_by_pid
            ;;
        port)
            stop_by_port
            ;;
        *)
            echo "用法: $0 [auto|pid|port]"
            echo "  auto  - 自动检测并停止（默认）"
            echo "  pid   - 仅通过PID文件停止"
            echo "  port  - 仅通过端口停止"
            exit 1
            ;;
    esac
    
    echo ""
    log_info "服务停止完成"
}

# 执行主函数
main "$@"
