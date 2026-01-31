#!/bin/bash

# RAG服务快速启动指南
# 一键启动脚本集合

echo "=========================================="
echo "  RAG服务管理脚本"
echo "=========================================="
echo ""
echo "请选择操作:"
echo "  1) 启动开发服务"
echo "  2) 启动生产服务"
echo "  3) 停止服务"
echo "  4) 重启服务"
echo "  5) 查看状态"
echo "  6) 查看日志"
echo "  0) 退出"
echo ""
read -p "请输入选项 [0-6]: " choice

case $choice in
    1)
        ./start.sh
        ;;
    2)
        ./start-prod.sh
        ;;
    3)
        ./stop.sh
        ;;
    4)
        ./restart.sh
        ;;
    5)
        ./status.sh
        ;;
    6)
        tail -f logs/server.log
        ;;
    0)
        echo "退出"
        exit 0
        ;;
    *)
        echo "无效选项"
        exit 1
        ;;
esac
