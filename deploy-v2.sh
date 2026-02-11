#!/bin/bash

# RAG服务部署脚本 v2.0
# 支持: Docker Compose 和 Kubernetes

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 日志函数
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 显示使用说明
show_usage() {
    cat << 'EOF'
RAG服务部署脚本 v2.0

使用方法:
    ./deploy-v2.sh [COMMAND] [ENV]

COMMAND:
    build       构建Docker镜像
    compose     使用Docker Compose部署
    k8s         使用Kubernetes部署
    stop        停止服务
    restart     重启服务
    status      查看服务状态
    logs        查看日志

ENV:
    dev         开发环境 (默认)
    prod        生产环境

示例:
    ./deploy-v2.sh build dev
    ./deploy-v2.sh compose prod
    ./deploy-v2.sh k8s prod

EOF
}

# 检查依赖
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装"
        exit 1
    fi
    log_info "Docker: $(docker --version)"
}

check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl未安装"
        exit 1
    fi
    log_info "kubectl: $(kubectl version --client --short 2>/dev/null || echo 'unknown')"
}

# 构建镜像
build_image() {
    local env=${1:-dev}
    local tag="rag-service:${env}"

    log_info "构建镜像: ${tag}"
    check_docker

    docker build -t ${tag} -f Dockerfile .
    [ "$env" = "prod" ] && docker tag ${tag} rag-service:latest
    log_info "构建完成"
}

# Docker Compose部署
deploy_compose() {
    local env=${1:-dev}

    log_info "Docker Compose部署: ${env}"
    check_docker

    docker-compose -f docker-compose.yml down
    docker-compose -f docker-compose.yml build
    docker-compose -f docker-compose.yml up -d

    log_info "部署完成!"
    log_info "API: http://localhost:8000/docs"
    log_info "Grafana: http://localhost:3001"
}

# Kubernetes部署
deploy_k8s() {
    local env=${1:-dev}

    log_info "Kubernetes部署: ${env}"
    check_kubectl

    kubectl apply -f k8s/
    kubectl wait --for=condition=available --timeout=300s \
        deployment/rag-service -n rag-service

    log_info "K8s部署完成!"
    kubectl get all -n rag-service
}

# 主函数
main() {
    local command=${1:-help}
    local env=${2:-dev}

    case $command in
        build) build_image "$env" ;;
        compose) deploy_compose "$env" ;;
        k8s) deploy_k8s "$env" ;;
        stop) docker-compose down 2>/dev/null || kubectl delete -f k8s/ 2>/dev/null ;;
        status) docker-compose ps 2>/dev/null || kubectl get all -n rag-service ;;
        *) show_usage ;;
    esac
}

main "$@"
