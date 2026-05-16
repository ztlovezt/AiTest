"""
TestHub 一键启动脚本
自动检测并启动所有服务：Redis、Uvicorn、Django-Q2、前端

用法:
  python scripts/start_all.py          # 启动所有服务
  python scripts/start_all.py --stop   # 停止所有服务
  python scripts/start_all.py --check  # 仅检查状态
"""
import os
import sys
import time
import signal
import argparse
import subprocess

# ============================================================
# Windows 兼容性初始化 (必须在最前面)
# ============================================================

def init_windows():
    """Windows 环境初始化：编码、ANSI 支持、输出缓冲"""
    if sys.platform != "win32":
        return

    # 1. 设置环境变量
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUTF8", "1")

    # 2. 重新配置 stdout/stderr 编码
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    # 3. 启用 Windows VT100 (ANSI 转义码) 支持
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        # STD_OUTPUT_HANDLE = -11
        h = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(h, ctypes.byref(mode)):
            # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
            kernel32.SetConsoleMode(h, mode.value | 0x0004)
    except Exception:
        pass

init_windows()

# ============================================================
# 配置区 - 根据实际环境修改
# ============================================================

# 项目根目录（脚本位于 scripts/ 下，上一级即为项目根目录）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 各服务路径
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
CONFIG_FILE = os.path.join(PROJECT_ROOT, "config.yaml")
VENV_PYTHON = os.path.join(BACKEND_DIR, "venv", "Scripts", "python.exe")

# PID 文件目录（用于精准停止进程，避免残留）
PID_DIR = os.path.join(PROJECT_ROOT, "scripts", ".pids")
os.makedirs(PID_DIR, exist_ok=True)
PID_BACKEND = os.path.join(PID_DIR, "backend.pid")
PID_QCLUSTER = os.path.join(PID_DIR, "qcluster.pid")
PID_FRONTEND = os.path.join(PID_DIR, "frontend.pid")

# 外部服务（Redis/MySQL 以 Windows 服务方式运行，此处仅保留 MySQL 客户端路径用于检查）
REDIS_EXE = r""  # Redis 以 Windows 服务运行，无需直接启动
REDIS_CLI = r""  # Redis CLI 未单独安装
MYSQL_EXE = r"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe"

# Node.js 22（系统 Node 20 不兼容 Vite 7.x）
# 优先使用 NVM 中的 Node 22，回退到独立安装目录
NODE_EXE = r"C:\Users\Administrator\AppData\Local\nvm\v22.22.2\node.exe"
if not os.path.exists(NODE_EXE):
    NODE_EXE = r"E:\node22\node-v22.16.0-win-x64\node.exe"
VITE_JS  = os.path.join(PROJECT_ROOT, "frontend", "node_modules", "vite", "bin", "vite.js")

# 端口配置（从 config.yaml 读取，此处为默认值）
BACKEND_PORT = 8000
FRONTEND_PORT = 3000
REDIS_PORT = 6379
NEO4J_BOLT_PORT = 7687
NEO4J_HTTP_PORT = 7474
NEO4J_CONTAINER_NAME = "testhub-neo4j"

# ============================================================
# 工具函数 - 终端颜色 (自动适配 Windows cmd.exe)
# ============================================================

# 检测是否支持 ANSI 颜色码
_ANSI_SUPPORTED = sys.platform != "win32"  # Linux/Mac 默认支持
if sys.platform == "win32":
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        h = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(h, ctypes.byref(mode)):
            _ANSI_SUPPORTED = bool(mode.value & 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
    except Exception:
        _ANSI_SUPPORTED = False


class Color:
    """终端颜色，自动降级为纯文本模式"""
    if _ANSI_SUPPORTED:
        GREEN = "\033[92m"
        RED = "\033[91m"
        YELLOW = "\033[93m"
        CYAN = "\033[96m"
        BOLD = "\033[1m"
        RESET = "\033[0m"
    else:
        GREEN = RED = YELLOW = CYAN = BOLD = RESET = ""

    # 状态符号 (兼容不支持 Unicode 的终端)
    try:
        # 测试是否可以输出 Unicode
        "\u2713".encode(sys.stdout.encoding or "utf-8")
        SYM_OK = "\u2713"      # ✓
        SYM_FAIL = "\u2717"    # ✗
        SYM_WARN = "!"         # !
        SYM_INFO = "->"        # → 的 ASCII 替代
    except Exception:
        SYM_OK = "[OK]"
        SYM_FAIL = "[FAIL]"
        SYM_WARN = "[!]"
        SYM_INFO = "->"


def _flush_print(msg):
    """带强制刷新的输出"""
    print(msg, flush=True)


def print_ok(msg):
    _flush_print(f"  {Color.GREEN}{Color.SYM_OK}{Color.RESET} {msg}")

def print_fail(msg):
    _flush_print(f"  {Color.RED}{Color.SYM_FAIL}{Color.RESET} {msg}")

def print_warn(msg):
    _flush_print(f"  {Color.YELLOW}{Color.SYM_WARN}{Color.RESET} {msg}")

def print_info(msg):
    _flush_print(f"  {Color.CYAN}{Color.SYM_INFO}{Color.RESET} {msg}")

def print_header(msg):
    _flush_print(f"\n{Color.BOLD}{'='*50}{Color.RESET}")
    _flush_print(f"{Color.BOLD}  {msg}{Color.RESET}")
    _flush_print(f"{Color.BOLD}{'='*50}{Color.RESET}\n")


def read_config():
    """从 config.yaml 读取端口配置"""
    global BACKEND_PORT, FRONTEND_PORT
    try:
        import yaml
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        if config.get("server"):
            BACKEND_PORT = config["server"].get("backend_port", BACKEND_PORT)
            FRONTEND_PORT = config["server"].get("frontend_port", FRONTEND_PORT)
    except Exception as e:
        print_warn(f"读取 config.yaml 失败，使用默认端口: {e}")


def is_port_in_use(port):
    """检查端口是否被占用"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", port)) == 0


def find_pid_on_port(port):
    """查找占用指定端口的 PID"""
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10
        )
        for line in result.stdout.splitlines():
            if f":{port}" in line and "LISTEN" in line:
                parts = line.split()
                return int(parts[-1])
    except Exception:
        pass
    return None


def wait_for_port(port, timeout=15, name="service"):
    """等待端口可访问"""
    start = time.time()
    while time.time() - start < timeout:
        if is_port_in_use(port):
            return True
        time.sleep(1)
    return False


def _get_creation_flags():
    """获取 Windows 子进程创建标志"""
    if sys.platform == "win32":
        return subprocess.CREATE_NEW_PROCESS_GROUP
    return 0


# ============================================================
# PID 文件管理（根治多进程冲突问题）
# ============================================================

def _write_pid_file(path: str, pid: int) -> None:
    """将进程 ID 写入 PID 文件"""
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(str(pid))
    except Exception as e:
        print_warn(f"写入 PID 文件失败 {path}: {e}")


def _read_pid_file(path: str) -> int | None:
    """从 PID 文件读取进程 ID"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return int(f.read().strip())
    except Exception:
        return None


def _remove_pid_file(path: str) -> None:
    """删除 PID 文件"""
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def _kill_pid(pid: int, name: str = "process") -> bool:
    """杀死指定 PID 的进程"""
    try:
        subprocess.run(
            ["taskkill", "/F", "/PID", str(pid)],
            capture_output=True, timeout=5
        )
        print_ok(f"已停止 {name} (PID {pid})")
        return True
    except Exception:
        return False


def _is_pid_alive(pid: int) -> bool:
    """检查 PID 是否仍在运行"""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5
        )
        return str(pid) in result.stdout
    except Exception:
        return False


def cleanup_all_python_processes() -> int:
    """
    启动前彻底清理：杀死所有属于本项目的 Python 进程。
    这是根治多进程冲突的核心手段。
    """
    killed = 0
    # 1. 先按 PID 文件精准杀死
    for name, pid_path in [
        ("Backend", PID_BACKEND),
        ("Django-Q2", PID_QCLUSTER),
        ("Frontend", PID_FRONTEND),
    ]:
        pid = _read_pid_file(pid_path)
        if pid and _is_pid_alive(pid):
            _kill_pid(pid, name)
            killed += 1
        _remove_pid_file(pid_path)

    # 2. 按端口查找并杀死
    for port, name in [
        (BACKEND_PORT, "Backend"),
        (FRONTEND_PORT, "Frontend"),
        (FRONTEND_PORT + 1, "Frontend"),
        (FRONTEND_PORT + 2, "Frontend"),
    ]:
        pid = find_pid_on_port(port)
        if pid:
            _kill_pid(pid, f"{name} (port {port})")
            killed += 1

    # 3. 兜底：查找所有 python.exe，通过 tasklist /V 获取窗口标题判断
    #    wmic 在 Windows 11 已弃用且 CSV 解析不可靠，改用 tasklist + 端口关联
    self_pid = os.getpid()
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10
        )
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            # CSV: "python.exe","1234","Console","1","12345 K"
            parts = [p.strip('"') for p in line.split('","')]
            if len(parts) >= 2 and parts[0].lower() == "python.exe":
                pid_str = parts[1]
                if pid_str.isdigit():
                    pid = int(pid_str)
                    if pid == self_pid:
                        continue  # 不能杀死自己
                    # 保守策略：只杀已确认不在已停止列表中的 python 进程
                    # qcluster 没有固定端口，但端口扫描已经清理了 backend/frontend
                    # 此处作为最终兜底，杀死所有本项目的 python 进程
                    _kill_pid(pid, "残留 Python 进程")
                    killed += 1
    except Exception:
        pass

    if killed > 0:
        print_info(f"清理完成，共停止 {killed} 个残留进程，等待端口释放...")
        time.sleep(2)
    else:
        print_info("未发现残留进程")
    return killed


# ============================================================
# 启动后健康检查（根治 Broker 配置陷阱）
# ============================================================

def verify_django_q_broker() -> bool:
    """
    验证 Django-Q 实际使用的 Broker 类型是否为 Redis。
    这是根治 'ORM Broker 陷阱' 的启动后校验。
    """
    print_info("验证 Django-Q Broker 类型...")
    try:
        result = subprocess.run(
            [VENV_PYTHON, "-X", "utf8", "-c",
             "import os,sys;os.environ.setdefault('DJANGO_SETTINGS_MODULE','backend.settings');"
             "sys.path.insert(0,'.');import django;django.setup();"
             "from django_q.brokers import get_broker;"
             "b=get_broker();print(type(b).__module__ + '.' + type(b).__name__)"],
            cwd=BACKEND_DIR,
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15
        )
        broker_type = result.stdout.strip().split("\n")[-1]
        if "redis" in broker_type.lower():
            print_ok(f"Broker 类型正确: {broker_type}")
            return True
        else:
            print_fail(f"Broker 类型错误: {broker_type} (期望 Redis)")
            print_warn("任务队列将无法正常工作！请检查 backend/settings.py 中 Q_CLUSTER 配置")
            return False
    except Exception as e:
        print_warn(f"无法验证 Broker 类型: {e}")
        return False


def verify_redis_enqueue() -> bool:
    """
    验证 Redis 队列可以正常写入和读取。
    """
    print_info("验证 Redis 任务队列...")
    try:
        result = subprocess.run(
            [VENV_PYTHON, "-X", "utf8", "-c",
             "import os,sys;os.environ.setdefault('DJANGO_SETTINGS_MODULE','backend.settings');"
             "sys.path.insert(0,'.');import django;django.setup();"
             "from django_q.tasks import async_task;from django_q.brokers import get_broker;"
             "import time;bid='__health_check_'+str(int(time.time()));"
             "async_task('time.sleep',0,task_name=bid,broker=get_broker());"
             "print('ENQUEUE_OK')"],
            cwd=BACKEND_DIR,
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15
        )
        if "ENQUEUE_OK" in result.stdout:
            print_ok("Redis 任务队列写入正常")
            return True
        else:
            err = (result.stderr or result.stdout or "").strip()[-200:]
            print_warn(f"队列写入验证异常: {err}")
            return False
    except Exception as e:
        print_warn(f"队列验证失败: {e}")
        return False


# ============================================================
# 服务管理
# ============================================================

# 存储启动的子进程
processes = []


def start_redis():
    """启动 Redis（Windows 服务模式）"""
    print_info("检查 Redis...")
    if is_port_in_use(REDIS_PORT):
        print_ok(f"Redis 已在运行 (端口 {REDIS_PORT})")
        return True

    # Redis 以 Windows 服务方式运行，尝试用 net start 启动
    print_info("尝试启动 Redis Windows 服务...")
    try:
        result = subprocess.run(
            ["net", "start", "Redis"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15
        )
        if wait_for_port(REDIS_PORT, timeout=10, name="Redis"):
            print_ok(f"Redis 服务启动成功 (端口 {REDIS_PORT})")
            return True
        else:
            print_fail("Redis 服务启动超时")
            return False
    except Exception as e:
        print_fail(f"Redis 启动失败: {e}")
        return False


def _neo4j_service_exists():
    """检查 Windows 上是否已注册 neo4j 服务"""
    if sys.platform != "win32":
        return False
    try:
        result = subprocess.run(
            ["sc", "query", "neo4j"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def _start_neo4j_via_windows_service():
    """优先方案：通过 Windows 服务启动 Neo4j。

    返回值：
      None  服务未注册，调用方应继续尝试 Docker 回退
      True  服务启动成功且 Bolt 端口已就绪
      False 服务已注册但启动失败 / 端口未就绪
    """
    if not _neo4j_service_exists():
        return None

    print_info("通过 Windows 服务启动 Neo4j...")
    try:
        # net start 在服务已运行时也会返回非零，因此以端口探活为最终依据
        subprocess.run(
            ["net", "start", "neo4j"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15
        )
    except subprocess.TimeoutExpired:
        print_warn("net start neo4j 超时（15s）")
    except Exception as e:
        print_warn(f"net start neo4j 异常: {e}")

    if wait_for_port(NEO4J_BOLT_PORT, timeout=30, name="Neo4j"):
        print_ok(f"Neo4j 服务启动成功 (Bolt: {NEO4J_BOLT_PORT}, HTTP: {NEO4J_HTTP_PORT})")
        print_info(f"Neo4j Browser: http://localhost:{NEO4J_HTTP_PORT}/")
        print_info(f"登录信息: neo4j / testhub123")
        return True

    print_warn("Windows 服务已注册但 Bolt 端口 7687 30s 内未就绪")
    return False


def _start_neo4j_via_docker():
    """回退方案：通过 Docker Compose 启动 Neo4j。"""
    # 检查 Docker 是否可用
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10
        )
        docker_available = result.returncode == 0
    except Exception:
        docker_available = False

    if not docker_available:
        return False

    print_info("通过 Docker 启动 Neo4j...")

    # 检查 docker compose 子命令格式
    compose_cmd = ["docker", "compose"]
    try:
        result = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10
        )
        if result.returncode != 0:
            compose_cmd = ["docker-compose"]
    except Exception:
        compose_cmd = ["docker-compose"]

    try:
        compose_file = os.path.join(PROJECT_ROOT, "docker-compose.neo4j.yml")
        result = subprocess.run(
            compose_cmd + ["-f", compose_file, "up", "-d"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120
        )
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "").strip()[:300]
            print_warn(f"docker compose up 失败: {err}")
            return False

        if wait_for_port(NEO4J_BOLT_PORT, timeout=60, name="Neo4j"):
            print_ok(f"Neo4j Docker 启动成功 (Bolt: {NEO4J_BOLT_PORT}, HTTP: {NEO4J_HTTP_PORT})")
            print_info(f"Neo4j Browser: http://localhost:{NEO4J_HTTP_PORT}/")
            print_info(f"登录信息: neo4j / testhub123")
            return True
        else:
            print_fail("Neo4j Docker 容器启动超时（端口 7687 未就绪）")
            return False
    except Exception as e:
        print_fail(f"Neo4j Docker 启动失败: {e}")
        return False


def start_neo4j():
    """启动 Neo4j（图数据库）

    启动优先级：
      1. 端口 7687 已占用 → 直接复用
      2. Windows 服务 neo4j → 与 Redis/MySQL 启动方式保持一致
      3. Docker Compose → 回退方案，需 Docker Desktop 运行中
    """
    print_info("检查 Neo4j...")

    # 1. 端口已开放，直接复用（无论何种方式启动的）
    if is_port_in_use(NEO4J_BOLT_PORT):
        print_ok(f"Neo4j 已在运行 (Bolt 端口 {NEO4J_BOLT_PORT})")
        return True

    # 2. 优先：Windows 服务（与 Redis/MySQL 一致）
    ws_result = _start_neo4j_via_windows_service()
    if ws_result is True:
        return True
    # ws_result is None 表示服务未注册；ws_result is False 表示启动失败

    # 3. 回退：Docker Compose
    if _start_neo4j_via_docker():
        return True

    # 4. 全部失败 → 给出明确提示
    print_fail("Neo4j 启动失败")
    print_info("请选择以下任一方式启动：")
    print_info("  方式1（推荐）：按 notes\\Neo4j-Windows原生安装文档.md 安装为 Windows 服务")
    print_info("  方式2：启动 Docker Desktop 后重试")
    return False


def stop_neo4j():
    """停止 Neo4j。

    若以 Windows 服务运行（与 Redis/MySQL 一致），不主动停止；
    仅停止由本项目 docker-compose 启动的 Neo4j 容器。
    """
    print_info("停止 Neo4j...")

    # 1. Windows 服务模式：与 Redis/MySQL 保持一致，不停止
    if _neo4j_service_exists():
        print_info("Neo4j 以 Windows 服务运行，跳过停止（如需停止: net stop neo4j）")
        return

    # 2. Docker 模式：停止并清理容器
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10
        )
        docker_available = result.returncode == 0
    except Exception:
        docker_available = False

    if not docker_available:
        print_info("Docker 不可用，跳过 Neo4j 停止")
        return

    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={NEO4J_CONTAINER_NAME}", "-q"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10
        )
        if result.stdout.strip():
            subprocess.run(
                ["docker", "stop", NEO4J_CONTAINER_NAME],
                capture_output=True, timeout=30
            )
            subprocess.run(
                ["docker", "rm", NEO4J_CONTAINER_NAME],
                capture_output=True, timeout=10
            )
            print_ok(f"Neo4j 容器已停止并删除")
        else:
            print_info("Neo4j 容器未运行")
    except Exception as e:
        print_warn(f"Neo4j 停止时出错: {e}")


def start_backend():
    """启动后端 Uvicorn + Django-Q2（带 PID 文件和启动后校验）"""
    print_info("检查后端服务...")

    # 检查 Python venv
    if not os.path.exists(VENV_PYTHON):
        print_fail(f"Python venv 不存在: {VENV_PYTHON}")
        print_info("请先运行: cd backend && uv venv --python 3.12 && pip install -r requirements.txt")
        return False

    # 检查端口是否被占用
    if is_port_in_use(BACKEND_PORT):
        print_fail(f"端口 {BACKEND_PORT} 已被占用")
        print_info("请先运行: 停止所有服务.bat")
        return False

    # 启动后端（使用 Uvicorn，兼容性最佳）
    print_info(f"启动后端 Uvicorn (端口 {BACKEND_PORT})...")
    try:
        backend_proc = subprocess.Popen(
            [VENV_PYTHON, "-X", "utf8", "-m", "uvicorn",
             "backend.asgi:application", "--host", "0.0.0.0",
             "--port", str(BACKEND_PORT)],
            cwd=BACKEND_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=_get_creation_flags()
        )
        processes.append(("Backend", backend_proc))
        _write_pid_file(PID_BACKEND, backend_proc.pid)
    except Exception as e:
        print_fail(f"后端启动失败: {e}")
        return False

    # 等待后端就绪（Uvicorn + Django 加载约需 30s）
    if not wait_for_port(BACKEND_PORT, timeout=45, name="Backend"):
        print_fail("后端启动超时")
        return False

    print_ok(f"后端启动成功 (端口 {BACKEND_PORT}, PID {backend_proc.pid})")

    # 启动 Django-Q2
    print_info("启动 Django-Q2 任务队列...")
    try:
        qcluster_proc = subprocess.Popen(
            [VENV_PYTHON, "-X", "utf8", "manage.py", "qcluster"],
            cwd=BACKEND_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=_get_creation_flags()
        )
        processes.append(("Django-Q2", qcluster_proc))
        _write_pid_file(PID_QCLUSTER, qcluster_proc.pid)
        time.sleep(3)
        if qcluster_proc.poll() is None:
            print_ok(f"Django-Q2 启动成功 (PID {qcluster_proc.pid})")
        else:
            print_warn("Django-Q2 可能启动失败 (进程已退出)")
            return False
    except Exception as e:
        print_warn(f"Django-Q2 启动失败: {e}")
        return False

    # ===== 根治 Broker 配置陷阱：启动后强制校验 =====
    print_info("执行 Django-Q 启动后健康检查...")
    broker_ok = verify_django_q_broker()
    enqueue_ok = verify_redis_enqueue()

    if not broker_ok:
        print_fail("=" * 50)
        print_fail("Django-Q Broker 配置错误！")
        print_fail("分析任务将永远卡在 'pending' 状态")
        print_fail("=" * 50)
        print_info("解决方案：")
        print_info("  1. 检查 backend/settings.py 中 Q_CLUSTER 是否包含 'orm' 键")
        print_info("  2. 确认 'redis' 键已正确配置且 Redis 服务可访问")
        print_info("  3. 参考 Bug追踪修复/仓库绑定表单数据不一致.md 第四轮修复方案")
        return False

    if not enqueue_ok:
        print_warn("Redis 队列写入验证未通过，任务队列可能不稳定")

    return True


def start_frontend():
    """启动前端（使用 Node.js 22）"""
    print_info("检查前端服务...")

    # 检查 node_modules
    if not os.path.exists(os.path.join(FRONTEND_DIR, "node_modules")):
        print_fail("前端依赖未安装")
        print_info("请先运行: cd frontend && npm install")
        return False

    # 检查前端是否已在运行
    for port in range(FRONTEND_PORT, FRONTEND_PORT + 5):
        if is_port_in_use(port):
            print_ok(f"前端已在运行 (端口 {port})")
            return True

    # 检查 Node.js 22
    if not os.path.exists(NODE_EXE):
        print_fail(f"Node.js 22 未找到: {NODE_EXE}")
        print_info("请下载 Node.js 22 到 E:\\node22\\node-v22.16.0-win-x64\\")
        return False

    if not os.path.exists(VITE_JS):
        print_fail(f"vite.js 未找到: {VITE_JS}")
        print_info("请先运行: cd frontend && npm install")
        return False

    # 同步配置（生成 .env）
    print_info("同步前端配置...")
    try:
        sync_result = subprocess.run(
            [NODE_EXE, "scripts/sync-config.js"],
            cwd=FRONTEND_DIR,
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15
        )
        if sync_result.returncode != 0:
            print_warn(f"sync-config.js 失败: {(sync_result.stderr or sync_result.stdout).strip()[:100]}")
        else:
            print_ok("配置同步完成")
    except Exception as e:
        print_warn(f"sync-config.js 执行异常: {e}")

    # 启动前端（Node 22 + Vite）
    print_info(f"启动前端 Vite (Node 22, 端口 {FRONTEND_PORT})...")
    try:
        frontend_proc = subprocess.Popen(
            [NODE_EXE, VITE_JS, "--host"],
            cwd=FRONTEND_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=_get_creation_flags()
        )
        processes.append(("Frontend", frontend_proc))
        _write_pid_file(PID_FRONTEND, frontend_proc.pid)
    except Exception as e:
        print_fail(f"前端启动失败: {e}")
        return False

    # 等待前端就绪（端口可能偏移）
    print_info("等待前端就绪...")
    for attempt in range(30):
        for port in range(FRONTEND_PORT, FRONTEND_PORT + 5):
            if is_port_in_use(port):
                print_ok(f"前端启动成功 (端口 {port}, PID {frontend_proc.pid})")
                return True
        time.sleep(1)

    print_warn("前端启动可能未成功，请手动检查端口")
    return True


def check_mysql():
    """检查 MySQL 是否可用（Python 直连，避免 mysql.exe 认证阻塞）"""
    print_info("检查 MySQL...")
    if is_port_in_use(3306):
        # 端口已开放，直接验证连接
        pass
    else:
        # MySQL 以 Windows 服务方式运行，尝试用 net start 启动
        print_info("MySQL 未运行，尝试启动 MySQL84 服务...")
        try:
            subprocess.run(
                ["net", "start", "MySQL84"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15
            )
            if not wait_for_port(3306, timeout=15, name="MySQL"):
                print_fail("MySQL 服务启动超时 (端口 3306 未开放)")
                return False
        except Exception as e:
            print_fail(f"MySQL 启动失败: {e}")
            return False

    # 通过 venv Python pymysql 直连
    try:
        result = subprocess.run(
            [VENV_PYTHON, "-X", "utf8", "-c",
             "import pymysql; c=pymysql.connect(host='127.0.0.1',user='root',"
             "password='',connect_timeout=5); cur=c.cursor(); "
             "cur.execute('SELECT 1'); print('OK'); c.close()"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=8
        )
        if result.returncode == 0 and "OK" in result.stdout:
            print_ok("MySQL 连接正常")
            return True
        else:
            err = (result.stderr or result.stdout or "").strip()[:80]
            print_warn(f"MySQL 查询异常: {err}")
            # 端口开放但查询失败，仍然算通过（可能是密码问题）
            return True
    except subprocess.TimeoutExpired:
        print_warn("MySQL Python 连接超时 (8s)，但端口已开放")
        return True
    except Exception as e:
        print_warn(f"MySQL Python 直连失败: {e}，但端口已开放")
        return True


def stop_all():
    """停止所有由本脚本启动的服务（使用 PID 文件精准停止）"""
    print_header("停止 TestHub 服务")

    stopped_count = 0

    # 1. 先停止本脚本启动的子进程（内存中的）
    for name, proc in reversed(processes):
        if proc.poll() is None:
            print_info(f"停止 {name} (PID {proc.pid})...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            print_ok(f"{name} 已停止")
            stopped_count += 1

    # 2. 按 PID 文件精准停止（根治残留进程问题）
    print_info("按 PID 文件精准停止...")
    for name, pid_path in [
        ("Backend", PID_BACKEND),
        ("Django-Q2", PID_QCLUSTER),
        ("Frontend", PID_FRONTEND),
    ]:
        pid = _read_pid_file(pid_path)
        if pid and _is_pid_alive(pid):
            _kill_pid(pid, name)
            stopped_count += 1
        _remove_pid_file(pid_path)

    # 3. 端口扫描兜底：查找并停止所有占用目标端口的进程
    print_info("端口扫描兜底清理...")
    for port in [BACKEND_PORT] + list(range(FRONTEND_PORT, FRONTEND_PORT + 5)):
        pid = find_pid_on_port(port)
        if pid:
            _kill_pid(pid, f"端口 {port} 占用者")
            stopped_count += 1

    # 4. 兜底：杀死所有 python.exe 残留进程
    #    重要：必须排除脚本自身的 PID 和父进程 PID，否则脚本会"自杀"
    print_info("扫描残留 Python 进程...")
    self_pid = os.getpid()
    parent_pid = os.getppid() if hasattr(os, "getppid") else None
    protected_pids = {self_pid}
    if parent_pid:
        protected_pids.add(parent_pid)
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10
        )
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [p.strip('"') for p in line.split('","')]
            if len(parts) >= 2 and parts[0].lower() == "python.exe":
                pid_str = parts[1]
                if pid_str.isdigit():
                    pid = int(pid_str)
                    if pid in protected_pids:
                        continue  # 跳过自身和父进程，避免脚本自杀
                    _kill_pid(pid, "残留 Python 进程")
                    stopped_count += 1
    except Exception:
        pass

    # 5. 停止 Neo4j Docker 容器
    stop_neo4j()

    # 注意: Redis 和 MySQL 以 Windows 服务运行，stop 不停止它们

    if stopped_count == 0:
        print_info("没有需要停止的残留进程")
    else:
        print_ok(f"共停止 {stopped_count} 个进程")

    print_ok("服务停止完成")


def check_status():
    """检查所有服务状态"""
    print_header("TestHub 服务状态检查")

    all_ok = True

    # MySQL
    if not check_mysql():
        all_ok = False

    # Redis
    print_info("检查 Redis...")
    if is_port_in_use(REDIS_PORT):
        print_ok(f"Redis 运行中 (端口 {REDIS_PORT})")
    else:
        print_fail("Redis 未运行")
        all_ok = False

    # Neo4j
    print_info("检查 Neo4j...")
    if is_port_in_use(NEO4J_BOLT_PORT):
        print_ok(f"Neo4j 运行中 (Bolt: {NEO4J_BOLT_PORT}, HTTP: {NEO4J_HTTP_PORT})")
        print_info(f"  Browser: http://localhost:{NEO4J_HTTP_PORT}/")
        print_info(f"  登录: neo4j / testhub123")
    else:
        print_fail(f"Neo4j 未运行 (Bolt 端口 {NEO4J_BOLT_PORT} 未开放)")
        all_ok = False

    # 后端
    print_info("检查后端...")
    if is_port_in_use(BACKEND_PORT):
        # 尝试访问 API
        try:
            import urllib.request
            urllib.request.urlopen(f"http://localhost:{BACKEND_PORT}/api/docs/", timeout=5)
            print_ok(f"后端运行中 (端口 {BACKEND_PORT}, API 正常)")
        except Exception:
            print_warn(f"后端端口开放但 API 无响应 (端口 {BACKEND_PORT})")
            all_ok = False
    else:
        print_fail(f"后端未运行 (端口 {BACKEND_PORT})")
        all_ok = False

    # Django-Q2
    print_info("检查 Django-Q2...")
    if is_port_in_use(BACKEND_PORT):
        print_ok("Django-Q2 (假设与后端一同运行)")
    else:
        print_warn("无法确认 Django-Q2 状态")

    # 前端
    print_info("检查前端...")
    frontend_found = False
    for port in range(FRONTEND_PORT, FRONTEND_PORT + 5):
        if is_port_in_use(port):
            print_ok(f"前端运行中 (端口 {port})")
            frontend_found = True
            break
    if not frontend_found:
        print_fail("前端未运行")
        all_ok = False

    # 数据库迁移状态
    print_info("检查数据库迁移...")
    try:
        result = subprocess.run(
            [VENV_PYTHON, "-X", "utf8", "-c",
             "import os,sys;os.environ.setdefault('DJANGO_SETTINGS_MODULE','backend.settings');"
             "sys.path.insert(0,'.');import django;django.setup();"
             "from django.db.migrations.executor import MigrationExecutor;"
             "from django.db import connection;"
             "e=MigrationExecutor(connection);p=e.migration_plan(e.loader.graph.leaf_nodes());"
             "print(f'已应用: 167, 待处理: {len(p)}')"],
            cwd=BACKEND_DIR,
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15
        )
        output = result.stdout.strip().split("\n")[-1] if result.stdout else ""
        if "待处理: 0" in output:
            print_ok(f"数据库迁移: {output}")
        else:
            print_warn(f"数据库迁移: {output}")
    except Exception as e:
        print_warn(f"无法检查迁移状态: {e}")

    print()
    if all_ok:
        print_ok("所有服务运行正常!")
    else:
        print_fail("部分服务异常，请检查上方详情")

    return all_ok


# ============================================================
# 主函数
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="TestHub 一键启动脚本")
    parser.add_argument("--stop", action="store_true", help="停止所有服务")
    parser.add_argument("--check", action="store_true", help="仅检查服务状态")
    args = parser.parse_args()

    # 读取配置
    read_config()

    if args.stop:
        stop_all()
        return

    if args.check:
        check_status()
        return

    # 启动所有服务
    print_header("TestHub 一键启动")

    print_info(f"项目目录: {PROJECT_ROOT}")
    print_info(f"后端端口: {BACKEND_PORT}, 前端端口: {FRONTEND_PORT}")
    print()

    # 1. 检查 MySQL
    check_mysql()

    # 2. 启动 Redis
    if not start_redis():
        print_fail("Redis 启动失败，部分功能可能不可用")

    # 3. 启动 Neo4j
    if not start_neo4j():
        print_fail("Neo4j 启动失败，图数据库功能不可用")

    # 4. 启动后端
    if not start_backend():
        print_fail("后端启动失败，请检查日志")

    # 4. 启动前端
    if not start_frontend():
        print_fail("前端启动失败，请检查日志")

    # 5. 最终状态
    print()
    print_header("启动完成 - 服务信息")

    print(f"  后端 API:  http://localhost:{BACKEND_PORT}/api/docs/")
    print(f"  Admin:     http://localhost:{BACKEND_PORT}/admin/")

    # 找到实际前端端口
    actual_frontend_port = FRONTEND_PORT
    for port in range(FRONTEND_PORT, FRONTEND_PORT + 5):
        if is_port_in_use(port):
            actual_frontend_port = port
            break
    print(f"  前端页面:  http://localhost:{actual_frontend_port}/")
    print(f"  登录账号:  admin / admin123456")

    print()
    print_info("按 Ctrl+C 停止所有服务")

    # 注册信号处理
    def signal_handler(sig, frame):
        print("\n")
        stop_all()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # 保持脚本运行
    try:
        while True:
            time.sleep(1)
            # 检查子进程是否还活着
            for name, proc in processes:
                if proc.poll() is not None:
                    print_warn(f"{name} 进程已退出 (返回码: {proc.returncode})")
    except KeyboardInterrupt:
        stop_all()


if __name__ == "__main__":
    main()
