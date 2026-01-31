#!/bin/bash

echo "=========================================="
echo "  /search 路由诊断工具"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查函数
check_service() {
    local service_name=$1
    local port=$2
    local url=$3

    echo -n "检查 $service_name (端口 $port)... "
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo -e "${GREEN}运行中${NC}"
        echo -e "  ✓ 服务状态: ${GREEN}正常${NC}"

        # 测试 URL
        if [ -n "$url" ]; then
            if curl -s "$url" > /dev/null 2>&1; then
                echo -e "  ✓ URL 可访问: ${GREEN}$url${NC}"
            else
                echo -e "  ✗ URL 不可访问: ${RED}$url${NC}"
            fi
        fi
    else
        echo -e "${RED}未运行${NC}"
        echo -e "  ✗ 服务未在端口 $port 上运行"
    fi
    echo ""
}

# 检查 API 端点
check_api_endpoint() {
    local endpoint=$1
    local description=$2

    echo -n "测试 $description... "
    response=$(curl -s "$endpoint" 2>&1)
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}成功${NC}"
        echo -e "  响应: ${GREEN}200 OK${NC}"
        if echo "$response" | grep -q "error\|Error\|ERROR" 2>/dev/null; then
            echo -e "  ⚠ 警告: 响应中包含错误"
            echo "$response" | head -1
        fi
    else
        echo -e "${RED}失败${NC}"
        echo -e "  错误: $response"
    fi
    echo ""
}

echo "## 1. 服务状态检查"
echo "----------------------------------------"
check_service "后端服务" "8000" "http://localhost:8000/health"
check_service "前端服务" "3000" "http://localhost:3000"
check_service "向量数据库" "N/A" ""

echo "## 2. API 端点检查"
echo "----------------------------------------"
check_api_endpoint "http://localhost:8000/health" "健康检查端点"
check_api_endpoint "http://localhost:8000/api/retrieval/stats" "向量统计端点"

echo "## 3. 路由文件检查"
echo "----------------------------------------"

if [ -f "frontend/src/router/index.tsx" ]; then
    echo -e "✓ ${GREEN}路由配置文件存在${NC}"
    if grep -q "path: 'search'" frontend/src/router/index.tsx; then
        echo -e "  ✓ ${GREEN}/search 路由已配置${NC}"
    else
        echo -e "  ✗ ${RED}/search 路由未找到${NC}"
    fi
    if grep -q "SearchPage" frontend/src/router/index.tsx; then
        echo -e "  ✓ ${GREEN}SearchPage 已导入${NC}"
    else
        echo -e "  ✗ ${RED}SearchPage 未导入${NC}"
    fi
else
    echo -e "✗ ${RED}路由配置文件不存在${NC}"
fi

if [ -f "frontend/src/pages/SearchPage.tsx" ]; then
    echo -e "✓ ${GREEN}SearchPage.tsx 存在${NC}"
else
    echo -e "✗ ${RED}SearchPage.tsx 不存在${NC}"
fi
echo ""

echo "## 4. 配置文件检查"
echo "----------------------------------------"

if [ -f "frontend/vite.config.ts" ]; then
    echo -e "✓ ${GREEN}Vite 配置文件存在${NC}"
    if grep -q "changeOrigin: true" frontend/vite.config.ts; then
        echo -e "  ✓ ${GREEN}CORS 代理已配置${NC}"
    else
        echo -e "  ✗ ${RED}CORS 代理未配置${NC}"
    fi
    if grep -q "target: 'http://localhost:8000'" frontend/vite.config.ts; then
        echo -e "  ✓ ${GREEN}后端地址配置正确${NC}"
    else
        echo -e "  ✗ ${RED}后端地址配置可能不正确${NC}"
    fi
else
    echo -e "✗ ${RED}Vite 配置文件不存在${NC}"
fi
echo ""

echo "## 5. 依赖检查"
echo "----------------------------------------"

if [ -f "frontend/package.json" ]; then
    echo -e "✓ ${GREEN}package.json 存在${NC}"

    # 检查关键依赖
    dependencies=("react-router-dom" "axios" "lucide-react" "@tanstack/react-query")
    for dep in "${dependencies[@]}"; do
        if grep -q "\"$dep\"" frontend/package.json; then
            echo -e "  ✓ ${GREEN}$dep${NC}"
        else
            echo -e "  ✗ ${RED}$dep 未安装${NC}"
        fi
    done
else
    echo -e "✗ ${RED}package.json 不存在${NC}"
fi
echo ""

echo "## 6. 类型检查"
echo "----------------------------------------"
cd frontend

if npx tsc --noEmit 2>&1 | grep -q "error TS"; then
    echo -e "✗ ${RED}存在 TypeScript 错误${NC}"
    echo -e "  请运行: ${YELLOW}npx tsc --noEmit${NC} 查看详细错误"
else
    echo -e "✓ ${GREEN}TypeScript 编译通过${NC}"
fi
cd ..
echo ""

echo "## 7. 问题诊断和建议"
echo "----------------------------------------"

# 检查后端是否运行
if ! lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${RED}⚠ 后端服务未运行${NC}"
    echo -e "  建议: ${YELLOW}python main.py${NC}"
    echo ""
fi

# 检查前端是否运行
if ! lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${RED}⚠ 前端服务未运行${NC}"
    echo -e "  建议: ${YELLOW}cd frontend && npm run dev${NC}"
    echo ""
fi

# 检查 SearchPage 是否正确导出
if [ -f "frontend/src/pages/SearchPage.tsx" ]; then
    if ! grep -q "export default function SearchPage" frontend/src/pages/SearchPage.tsx && \
       ! grep -q "export default const SearchPage" frontend/src/pages/SearchPage.tsx; then
        echo -e "${RED}⚠ SearchPage 可能未正确导出${NC}"
        echo -e "  请检查: frontend/src/pages/SearchPage.tsx"
        echo ""
    fi
fi

echo "=========================================="
echo "  诊断完成"
echo "=========================================="
echo ""
echo -e "如果问题仍然存在，请："
echo "  1. 查看 SEARCH_ROUTE_DIAGNOSIS.md 获取详细诊断步骤"
echo "  2. 检查浏览器控制台（F12）的错误信息"
echo "  3. 检查后端和前端的日志输出"
echo ""
