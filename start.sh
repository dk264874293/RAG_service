#!/bin/bash

# RAG服务启动脚本
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

# 创建必要的目录
create_directories() {
    log_info "创建必要的目录..."
    mkdir -p data/uploads data/processed data/faiss_index data/cache logs
    log_info "目录创建完成"
}

# 检查Python环境
check_python() {
    log_info "检查Python环境..."
    if ! command -v python &> /dev/null; then
        log_error "Python未安装或不在PATH中"
        exit 1
    fi
    PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
    log_info "Python版本: $PYTHON_VERSION"
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."
    if [ ! -f "requirements.txt" ]; then
        log_error "requirements.txt 文件不存在"
        exit 1
    fi
    
    log_info "安装/更新依赖..."
    pip install -r requirements.txt -q
    log_info "依赖安装完成"
}

# 检查环境变量
check_env() {
    log_info "检查环境变量..."
    if [ ! -f ".env" ]; then
        log_warn ".env文件不存在，创建默认配置..."
        
        # 生成随机密钥
        SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
        
        cat > .env << EOF
# API密钥配置
DASHSCOPE_API_KEY=your_dashscope_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# JWT密钥（生产环境请使用强随机密钥）
SECRET_KEY=$SECRET_KEY
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 开发模式
DEBUG_MODE=True

# 文件上传配置
MAX_UPLOAD_SIZE=10485760
ENABLE_FILE_SECURITY_CHECK=True

# 分块配置
ENABLE_CHUNKING=True
CHUNK_SIZE=800
CHUNK_OVERLAP=100
EOF
        log_warn ".env文件已创建，请编辑并填入正确的API密钥"
    fi
}

# 停止已存在的服务
stop_existing_service() {
    if [ -f "logs/server.pid" ]; then
        OLD_PID=$(cat logs/server.pid)
        if ps -p $OLD_PID > /dev/null 2>&1; then
            log_warn "检测到运行中的服务 (PID: $OLD_PID)，正在停止..."
            kill $OLD_PID 2>/dev/null || true
            sleep 2
        fi
        rm -f logs/server.pid
    fi
    
    # 检查端口占用
    if lsof -Pi :8000 -sTCP:LISTEN -t > /dev/null 2>&1; then
        log_warn "端口8000被占用，尝试释放..."
        lsof -ti:8000 | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
}

# 启动开发服务器
start_dev_server() {
    log_info "启动RAG服务（开发模式）..."

    # 设置OpenMP环境变量，解决FAISS与其他库的冲突
    export KMP_DUPLICATE_LIB_OK=TRUE

    nohup python -m uvicorn src.app:app \
        --reload \
        --host 0.0.0.0 \
        --port 8000 \
        > logs/server.log 2>&1 &
    
    SERVER_PID=$!
    echo $SERVER_PID > logs/server.pid
    
    sleep 3
    
    if ps -p $SERVER_PID > /dev/null 2>&1; then
        log_info "✅ 服务启动成功！"
        log_info "PID: $SERVER_PID"
        log_info "日志文件: logs/server.log"
        echo ""
        echo -e "${BLUE}========================================${NC}"
        echo -e "${GREEN}  RAG服务已启动${NC}"
        echo -e "${BLUE}========================================${NC}"
        echo -e "  API文档: ${YELLOW}http://localhost:8000/docs${NC}"
        echo -e "  健康检查: ${YELLOW}http://localhost:8000/health/${NC}"
        echo -e "  前端地址: ${YELLOW}http://localhost:3000${NC}"
        echo -e "${BLUE}========================================${NC}"
        echo ""
        log_info "查看实时日志: tail -f logs/server.log"
        log_info "停止服务: ./stop.sh 或 ./stop.sh dev"
    else
        log_error "服务启动失败，请查看日志: logs/server.log"
        exit 1
    fi
}

# 主函数
main() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}    RAG服务启动脚本${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    
    create_directories
    check_python
    check_dependencies
    check_env
    stop_existing_service
    start_dev_server
}

# 执行主函数
main "$@"
