#!/bin/bash

# RAG服务生产环境启动脚本
# Author: 汪培良
# Date: 2026-01-29

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# 检查是否为生产环境
check_production_env() {
    if [ -f ".env" ] && grep -q "DEBUG_MODE=False" .env; then
        log_info "检测到生产环境配置"
    else
        log_warn "警告: .env中未设置DEBUG_MODE=False"
        read -p "是否继续启动生产模式？(y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "已取消启动"
            exit 0
        fi
    fi
}

# 启动生产服务器
start_prod_server() {
    log_info "启动RAG服务（生产模式）..."
    
    # 获取CPU核心数
    WORKERS=${WORKERS:-$(python -c "import os; print(os.cpu_count() or 1)")}
    
    log_info "工作进程数: $WORKERS"
    
    nohup python -m uvicorn src.app:app \
        --host 0.0.0.0 \
        --port 8000 \
        --workers $WORKERS \
        --access-log \
        --log-level info \
        > logs/server.log 2>&1 &
    
    SERVER_PID=$!
    echo $SERVER_PID > logs/server.pid
    
    sleep 3
    
    if ps -p $SERVER_PID > /dev/null 2>&1; then
        log_info "✅ 生产服务启动成功！"
        log_info "PID: $SERVER_PID"
        log_info "工作进程: $WORKERS"
        log_info "日志文件: logs/server.log"
        echo ""
        echo -e "${BLUE}========================================${NC}"
        echo -e "${GREEN}  RAG生产服务已启动${NC}"
        echo -e "${BLUE}========================================${NC}"
        echo -e "  API文档: ${YELLOW}http://localhost:8000/docs${NC}"
        echo -e "  健康检查: ${YELLOW}http://localhost:8000/health/${NC}"
        echo -e "  Prometheus: ${YELLOW}http://localhost:8000/metrics${NC}"
        echo -e "${BLUE}========================================${NC}"
        echo ""
        log_info "查看实时日志: tail -f logs/server.log"
        log_info "停止服务: ./stop.sh"
    else
        log_error "服务启动失败，请查看日志: logs/server.log"
        exit 1
    fi
}

# 主函数
main() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  RAG生产服务启动脚本${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    
    check_production_env
    start_prod_server
}

# 执行主函数
main "$@"
