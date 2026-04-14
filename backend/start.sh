#!/bin/bash

# Set UTF-8 encoding (Mac/Linux)
export LANG=en_US.UTF-8

echo "========================================"
echo "   TestHub Service Startup Script (Linux/Mac)"
echo "   Using Daphne ASGI Server"
echo "========================================"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# Check Python environment
echo "Checking Python environment..."

# Use virtual environment if available
if [ -f "venv/bin/python" ]; then
    echo "Found virtual environment: venv"
    PYTHON_CMD="venv/bin/python"
elif [ -f ".venv/bin/python" ]; then
    echo "Found virtual environment: .venv"
    PYTHON_CMD=".venv/bin/python"
elif [ -n "$VIRTUAL_ENV" ]; then
    echo "Already in virtual environment"
    PYTHON_CMD="python"
else
    # Use specified virtual environment
    VENV_PATH="/d/ENV/TestHub"
    if [ -f "$VENV_PATH/bin/python" ]; then
        echo "Using specified virtual environment: $VENV_PATH"
        PYTHON_CMD="$VENV_PATH/bin/python"
    else
        echo "Error: Virtual environment not found!"
        echo "Please create virtual environment or activate virtual environment"
        echo "Expected path: $VENV_PATH"
        exit 1
    fi
fi

echo "Python command: $PYTHON_CMD"
echo ""

# Activate virtual environment (optional, for setting environment variables)
if [ -f "$VENV_PATH/bin/activate" ]; then
    source "$VENV_PATH/bin/activate"
fi

# Check configuration file
# Note: Script is in backend directory, need to read config.yaml from parent directory
if [ ! -f "../config.yaml" ]; then
    echo "Error: Configuration file ../config.yaml not found"
    exit 1
fi

# Read port configuration from config.yaml
# Note: Script is in backend directory, need to read config.yaml from parent directory
BACKEND_PORT=$(grep "backend_port:" ../config.yaml | awk '{print $2}' | tr -d ' ')

# Use default port if not found
if [ -z "$BACKEND_PORT" ]; then
    BACKEND_PORT=8000
fi

echo "[1/2] Starting Daphne ASGI server (with WebSocket support)..."
echo "Starting backend server, port: $BACKEND_PORT"
echo "WebSocket support: ENABLED"

# 禁用 OneDNN 和其他优化以避免 PaddlePaddle 3.x 兼容性问题
export FLAGS_use_mkldnn=0
export FLAGS_enable_mkldnn=0
export FLAGS_enable_onednn=0
export FLAGS_cinn_new_group_scheduler=0
export FLAGS_enable_pir_api=0
export FLAGS_check_cuda_version=0
export FLAGS_skip_allocator_mem_check=1
export PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True

# Start Daphne server (ASGI with WebSocket support)
"$PYTHON_CMD" -m daphne -b 0.0.0.0 -p "$BACKEND_PORT" backend.asgi:application &
DAPHNE_PID=$!

sleep 2

# Check if process started successfully
if kill -0 $DAPHNE_PID 2>/dev/null; then
    echo "✓ Daphne server started (PID: $DAPHNE_PID)"
else
    echo "✗ Daphne server startup failed"
    exit 1
fi

echo "[2/2] Starting Django-Q task queue service..."

# Start Django-Q
"$PYTHON_CMD" manage.py qcluster &
QCLUSTER_PID=$!

sleep 2

# Check if process started successfully
if kill -0 $QCLUSTER_PID 2>/dev/null; then
    echo "✓ Django-Q cluster started (PID: $QCLUSTER_PID)"
else
    echo "✗ Django-Q cluster startup failed"
    kill $DJANGO_PID 2>/dev/null
    exit 1
fi

echo ""
echo "========================================"
echo "   All services started!"
echo "========================================"
echo ""
echo "Services:"
echo "  - Daphne ASGI Server (WebSocket enabled): http://127.0.0.1:$BACKEND_PORT"
echo "  - Django-Q Task Queue: Running"
echo ""
echo "Process information:"
echo "  - Daphne Server: PID $DAPHNE_PID"
echo "  - Django-Q Cluster: PID $QCLUSTER_PID"
echo ""
echo "Access URLs:"
echo "  - API: http://127.0.0.1:$BACKEND_PORT/api/"
echo "  - WebSocket: ws://127.0.0.1:$BACKEND_PORT/ws/"
echo "  - API Docs: http://127.0.0.1:$BACKEND_PORT/api/docs/"
echo "  - Admin: http://127.0.0.1:$BACKEND_PORT/admin/"
echo ""
echo "Tips:"
echo "  - Stop services: kill $DAPHNE_PID $QCLUSTER_PID"
echo "  - View logs: tail -f logs/daphne.log"
echo "  - View logs: tail -f logs/django_q.log"
echo ""

# Save PID to file
echo "$DAPHNE_PID" > daphne_server.pid
echo "$QCLUSTER_PID" > django_qcluster.pid

# Monitor process
trap cleanup SIGINT SIGTERM

cleanup() {
    echo ""
    echo "Stopping services..."
    kill $DAPHNE_PID 2>/dev/null
    kill $QCLUSTER_PID 2>/dev/null
    rm -f daphne_server.pid django_qcluster.pid
    echo "All services stopped"
    exit 0
}

# Keep script running (optional, if you want script to continue running)
wait
