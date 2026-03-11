#!/bin/bash

# 设置 UTF-8 编码（Mac/Linux）
export LANG=en_US.UTF-8

echo "========================================"
echo "   TestHub 服务启动脚本 (Linux/Mac)"
echo "========================================"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# 检测 Python 环境
echo "检测 Python 环境..."

# 优先使用虚拟环境中的 Python
if [ -f "venv/bin/python" ]; then
    echo "找到虚拟环境：venv"
    PYTHON_CMD="venv/bin/python"
elif [ -f ".venv/bin/python" ]; then
    echo "找到虚拟环境：.venv"
    PYTHON_CMD=".venv/bin/python"
elif [ -n "$VIRTUAL_ENV" ]; then
    echo "已在虚拟环境中"
    PYTHON_CMD="python"
else
    # 使用指定的虚拟环境
    VENV_PATH="/d/ENV/TestHub"
    if [ -f "$VENV_PATH/bin/python" ]; then
        echo "使用指定虚拟环境：$VENV_PATH"
        PYTHON_CMD="$VENV_PATH/bin/python"
    else
        echo "错误：未找到虚拟环境！"
        echo "请确保已创建虚拟环境或激活虚拟环境"
        echo "期望路径：$VENV_PATH"
        exit 1
    fi
fi

echo "Python 命令：$PYTHON_CMD"
echo ""

# 激活虚拟环境（可选，用于设置环境变量）
if [ -f "$VENV_PATH/bin/activate" ]; then
    source "$VENV_PATH/bin/activate"
fi

# 检查配置文件
if [ ! -f "config.yaml" ]; then
    echo "错误：配置文件 config.yaml 不存在"
    exit 1
fi

# 从 config.yaml 读取端口配置
BACKEND_PORT=$(grep "backend_port:" config.yaml | awk '{print $2}' | tr -d ' ')

# 如果没有找到端口配置，使用默认端口
if [ -z "$BACKEND_PORT" ]; then
    BACKEND_PORT=8000
fi

echo "[1/2] 启动 Django 开发服务器..."
echo "正在启动后端服务器，端口：$BACKEND_PORT"

# 启动 Django 服务器
"$PYTHON_CMD" manage.py runserver 0.0.0.0:"$BACKEND_PORT" &
DJANGO_PID=$!

sleep 2

# 检查进程是否成功启动
if kill -0 $DJANGO_PID 2>/dev/null; then
    echo "✓ Django 服务器已启动 (PID: $DJANGO_PID)"
else
    echo "✗ Django 服务器启动失败"
    exit 1
fi

echo "[2/2] 启动 Django-Q 任务队列服务..."

# 启动 Django-Q
"$PYTHON_CMD" manage.py qcluster &
QCLUSTER_PID=$!

sleep 2

# 检查进程是否成功启动
if kill -0 $QCLUSTER_PID 2>/dev/null; then
    echo "✓ Django-Q 集群已启动 (PID: $QCLUSTER_PID)"
else
    echo "✗ Django-Q 集群启动失败"
    kill $DJANGO_PID 2>/dev/null
    exit 1
fi

echo ""
echo "========================================"
echo "   所有服务已启动！"
echo "========================================"
echo ""
echo "进程信息："
echo "  - Django Server: PID $DJANGO_PID"
echo "  - Django-Q Cluster: PID $QCLUSTER_PID"
echo ""
echo "提示："
echo "  - 停止服务：kill $DJANGO_PID $QCLUSTER_PID"
echo "  - 查看日志：tail -f logs/django_server.log"
echo "  - 查看日志：tail -f logs/django_q.log"
echo ""

# 保存 PID 到文件
echo "$DJANGO_PID" > django_server.pid
echo "$QCLUSTER_PID" > django_qcluster.pid

# 监控进程
trap cleanup SIGINT SIGTERM

cleanup() {
    echo ""
    echo "正在关闭服务..."
    kill $DJANGO_PID 2>/dev/null
    kill $QCLUSTER_PID 2>/dev/null
    rm -f django_server.pid django_qcluster.pid
    echo "所有服务已停止"
    exit 0
}

# 保持脚本运行（可选，如果希望脚本持续运行）
wait
