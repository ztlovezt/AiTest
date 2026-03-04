#!/bin/bash

# TestHub 启动脚本

echo "========================================"
echo "   TestHub 服务启动脚本"
echo "========================================"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 检查虚拟环境
if [ -d "venv" ]; then
    echo "激活虚拟环境..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "激活虚拟环境..."
    source .venv/bin/activate
elif [ -n "$VIRTUAL_ENV" ]; then
    echo "虚拟环境已激活"
else
    echo "警告：未找到虚拟环境，使用系统Python"
fi

echo ""
echo "[1/2] 启动 Django 开发服务器..."
python manage.py runserver &
DJANGO_PID=$!

sleep 2

echo ""
echo "[2/2] 启动 Django-Q 任务队列服务..."
python manage.py qcluster &
QCLUSTER_PID=$!

echo ""
echo "========================================"
echo "   所有服务已启动！"
echo "========================================"
echo ""
echo "服务信息："
echo "  - Django Server: http://localhost:8000"
echo "  - API 文档: http://localhost:8000/api/docs/"
echo "  - Admin 后台: http://localhost:8000/admin/"
echo ""
echo "提示："
echo "  - 按 Ctrl+C 停止所有服务"
echo "  - 查看日志请查看 logs/ 目录下的日志文件"
echo ""

# 保存进程ID
echo $DJANGO_PID > .django_server.pid
echo $QCLUSTER_PID > .qcluster.pid

# 等待进程
wait
