#!/bin/bash

# RAG服务状态检查脚本
# Author: 汪培良
# Date: 2026-01-29

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 项目路径
PROJECT_DIR="/Users/wangpeiliang/Desktop/AI/RAG_service"
cd "$PROJECT_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}    RAG服务状态检查${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查服务进程
check_process() {
    echo -e "${CYAN}[1] 服务进程检查${NC}"
    
    if [ -f "logs/server.pid" ]; then
        PID=$(cat logs/server.pid)
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "  ${GREEN}✓${NC} 服务运行中 (PID: $PID)"
            
            # 显示进程详情
            echo ""
            echo "  进程详情:"
            ps -p $PID -o pid,ppid,%cpu,%mem,etime,command | while read line; do
                echo "    $line"
            done
        else
            echo -e "  ${RED}✗${NC} PID文件存在但进程未运行"
            echo "  清理PID文件..."
            rm -f logs/server.pid
        fi
    else
        echo -e "  ${RED}✗${NC} 服务未运行（未找到PID文件）"
    fi
    echo ""
}

# 检查端口占用
check_port() {
    echo -e "${CYAN}[2] 端口占用检查${NC}"
    
    if lsof -Pi :8000 -sTCP:LISTEN -t > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} 端口8000已监听"
        
        echo ""
        echo "  端口详情:"
        lsof -Pi :8000 -sTCP:LISTEN | while read line; do
            echo "    $line"
        done
    else
        echo -e "  ${RED}✗${NC} 端口8000未监听"
    fi
    echo ""
}

# 检查服务健康状态
check_health() {
    echo -e "${CYAN}[3] 健康状态检查${NC}"
    
    if command -v curl > /dev/null 2>&1; then
        HEALTH_CHECK=$(curl -s http://localhost:8000/health/ 2>/dev/null || echo "failed")
        
        if [[ $HEALTH_CHECK == *"healthy"* ]]; then
            echo -e "  ${GREEN}✓${NC} 服务健康: OK"
        else
            echo -e "  ${RED}✗${NC} 服务健康检查失败"
        fi
    else
        echo -e "  ${YELLOW}⚠${NC} curl未安装，跳过健康检查"
    fi
    echo ""
}

# 检查日志文件
check_logs() {
    echo -e "${CYAN}[4] 日志文件检查${NC}"
    
    if [ -f "logs/server.log" ]; then
        FILE_SIZE=$(du -h logs/server.log | cut -f1)
        LINE_COUNT=$(wc -l < logs/server.log)
        echo -e "  ${GREEN}✓${NC} 日志文件存在"
        echo "    大小: $FILE_SIZE"
        echo "    行数: $LINE_COUNT"
        echo ""
        
        echo "  最后5行日志:"
        tail -n 5 logs/server.log | while read line; do
            if [[ $line == *"ERROR"* ]]; then
                echo -e "    ${RED}$line${NC}"
            elif [[ $line == *"WARNING"* ]]; then
                echo -e "    ${YELLOW}$line${NC}"
            else
                echo "    $line"
            fi
        done
    else
        echo -e "  ${YELLOW}⚠${NC} 日志文件不存在"
    fi
    echo ""
}

# 检查数据目录
check_directories() {
    echo -e "${CYAN}[5] 数据目录检查${NC}"
    
    DIRS=("data/uploads" "data/processed" "data/faiss_index" "data/cache" "logs")
    
    for dir in "${DIRS[@]}"; do
        if [ -d "$dir" ]; then
            FILE_COUNT=$(find "$dir" -type f | wc -l | awk '{print $1}')
            DIR_SIZE=$(du -sh "$dir" 2>/dev/null | cut -f1)
            echo -e "  ${GREEN}✓${NC} $dir"
            echo "    文件数: $FILE_COUNT, 大小: $DIR_SIZE"
        else
            echo -e "  ${RED}✗${NC} $dir (不存在)"
        fi
    done
    echo ""
}

# 检查环境配置
check_env() {
    echo -e "${CYAN}[6] 环境配置检查${NC}"
    
    if [ -f ".env" ]; then
        echo -e "  ${GREEN}✓${NC} .env文件存在"
        
        echo ""
        echo "  关键配置:"
        grep -E "^(DASHSCOPE_API_KEY|OPENAI_API_KEY|SECRET_KEY|DEBUG_MODE)" .env | while read line; do
            KEY=$(echo "$line" | cut -d'=' -f1)
            VALUE=$(echo "$line" | cut -d'=' -f2)
            
            if [[ $KEY == *"KEY"* ]]; then
                if [[ $VALUE == "your_"* ]] || [[ -z $VALUE ]]; then
                    echo -e "    ${RED}$Key:${NC} 未配置"
                else
                    echo -e "    ${GREEN}$Key:${NC} ✓"
                fi
            else
                echo "    $KEY: $VALUE"
            fi
        done
    else
        echo -e "  ${RED}✗${NC} .env文件不存在"
    fi
    echo ""
}

# 显示访问地址
show_access_info() {
    echo -e "${CYAN}[7] 访问地址${NC}"
    echo ""
    echo "  ${BLUE}API文档:${NC}     http://localhost:8000/docs"
    echo "  ${BLUE}ReDoc文档:${NC}   http://localhost:8000/redoc"
    echo "  ${BLUE}健康检查:${NC}   http://localhost:8000/health/"
    echo "  ${BLUE}Prometheus:${NC}  http://localhost:8000/metrics"
    echo "  ${BLUE}前端应用:${NC}   http://localhost:3000"
    echo ""
}

# 主函数
main() {
    check_process
    check_port
    check_health
    check_logs
    check_directories
    check_env
    show_access_info
    
    echo -e "${BLUE}========================================${NC}"
}

# 执行主函数
main "$@"
