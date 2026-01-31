#!/bin/bash

# RAG服务一键部署脚本
# 适用于首次部署或完整重置

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  RAG服务一键部署脚本${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 项目路径
PROJECT_DIR="/Users/wangpeiliang/Desktop/AI/RAG_service"
cd "$PROJECT_DIR"

# 步骤1: 环境检查
echo -e "${CYAN}[步骤 1/6] 环境检查${NC}"
echo "  检查Python版本..."
python --version || { echo -e "${RED}✗ Python未安装${NC}"; exit 1; }
echo -e "  ${GREEN}✓${NC} Python已安装"
echo ""

# 步骤2: 创建虚拟环境（可选）
echo -e "${CYAN}[步骤 2/6] 虚拟环境${NC}"
if [ ! -d "venv" ]; then
    echo "  创建虚拟环境..."
    python -m venv venv
    echo -e "  ${GREEN}✓${NC} 虚拟环境创建完成"
else
    echo -e "  ${YELLOW}⚠${NC} 虚拟环境已存在，跳过"
fi
echo ""

# 步骤3: 激活虚拟环境并安装依赖
echo -e "${CYAN}[步骤 3/6] 安装依赖${NC}"
if [ -d "venv" ]; then
    source venv/bin/activate
fi
echo "  安装Python依赖..."
pip install -q -r requirements.txt
echo -e "  ${GREEN}✓${NC} 依赖安装完成"
echo ""

# 步骤4: 创建必要目录
echo -e "${CYAN}[步骤 4/6] 创建目录${NC}"
mkdir -p data/uploads data/processed data/faiss_index data/cache logs
echo -e "  ${GREEN}✓${NC} 目录创建完成"
echo ""

# 步骤5: 配置环境变量
echo -e "${CYAN}[步骤 5/6] 配置环境变量${NC}"
if [ ! -f ".env" ]; then
    echo "  创建.env文件..."
    SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
    
    cat > .env << EOF
# API密钥配置（请手动填入）
DASHSCOPE_API_KEY=your_dashscope_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# JWT密钥（已自动生成）
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
    echo -e "  ${GREEN}✓${NC} .env文件已创建"
    echo -e "  ${YELLOW}⚠${NC}  请编辑.env文件并填入正确的API密钥！"
    echo ""
    read -p "是否现在编辑.env文件？(y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ${EDITOR:-nano} .env
    fi
else
    echo -e "  ${YELLOW}⚠${NC} .env文件已存在"
fi
echo ""

# 步骤6: 启动服务
echo -e "${CYAN}[步骤 6/6] 启动服务${NC}"
echo "  启动开发服务器..."
./start.sh

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "后续操作:"
echo "  1. 编辑.env文件，填入API密钥"
echo "  2. 重启服务: ./restart.sh"
echo "  3. 查看状态: ./status.sh"
echo "  4. 查看文档: http://localhost:8000/docs"
echo ""
