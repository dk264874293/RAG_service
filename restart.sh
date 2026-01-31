#!/bin/bash

# RAG服务重启脚本
# Author: 汪培良
# Date: 2026-01-29

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}    RAG服务重启${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo -e "${YELLOW}正在停止服务...${NC}"
./stop.sh

echo ""
echo -e "${YELLOW}等待2秒...${NC}"
sleep 2

echo ""
echo -e "${YELLOW}正在启动服务...${NC}"
./start.sh

echo ""
echo -e "${GREEN}✅ 重启完成！${NC}"
