"""
TestHub 服务状态检查脚本
全面检测所有服务的运行状态和健康度

用法:
  python scripts/check_status.py           # 完整检查
  python scripts/check_status.py --json    # JSON 格式输出
  python scripts/check_status.py --quiet   # 仅输出异常项
"""
import os
import sys
import json
import time
import socket
import argparse
import subprocess

# ============================================================
# Windows 兼容性初始化
# ============================================================

def init_windows():
    """Windows 环境初始化：编码、ANSI 支持、输出缓冲"""
    if sys.platform != "win32":
        return

    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUTF8", "1")

    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    # 启用 Windows VT100 (ANSI 转义码) 支持
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        h = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(h, ctypes.byref(mode)):
            kernel32.SetConsoleMode(h, mode.value | 0x0004)
    except Exception:
        pass

init_windows()

# ============================================================
# 配置区
# ============================================================

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
CONFIG_FILE = os.path.join(PROJECT_ROOT, "config.yaml")
VENV_PYTHON = os.path.join(BACKEND_DIR, "venv", "Scripts", "python.exe")

REDIS_EXE = r""  # Redis 以 Windows 服务运行
REDIS_CLI = r""  # Redis CLI 未单独安装
MYSQL_EXE = r"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe"

BACKEND_PORT = 8000
FRONTEND_PORT = 3000
REDIS_PORT = 6379
MYSQL_PORT = 3306
NEO4J_HTTP_PORT = 7474
NEO4J_BOLT_PORT = 7687

# ============================================================
# 终端颜色 (自动适配 Windows cmd.exe)
# ============================================================

_ANSI_SUPPORTED = sys.platform != "win32"
if sys.platform == "win32":
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        h = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(h, ctypes.byref(mode)):
            _ANSI_SUPPORTED = bool(mode.value & 0x0004)
    except Exception:
        _ANSI_SUPPORTED = False


class Color:
    if _ANSI_SUPPORTED:
        GREEN = "\033[92m"
        RED = "\033[91m"
        YELLOW = "\033[93m"
        CYAN = "\033[96m"
        BOLD = "\033[1m"
        DIM = "\033[2m"
        RESET = "\033[0m"
    else:
        GREEN = RED = YELLOW = CYAN = BOLD = DIM = RESET = ""

    try:
        "\u2713".encode(sys.stdout.encoding or "utf-8")
        SYM_OK = "\u2713"
        SYM_FAIL = "\u2717"
        SYM_WARN = "!"
        SYM_SKIP = "-"
    except Exception:
        SYM_OK = "[OK]"
        SYM_FAIL = "[FAIL]"
        SYM_WARN = "[!]"
        SYM_SKIP = "[-]"


# ============================================================
# 检查项
# ============================================================

def check_port(host, port):
    """检查端口是否可连接"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(3)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False


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


def check_mysql(status):
    """检查 MySQL 服务（优先 Python 直连，回退端口探测）"""
    item = {
        "name": "MySQL",
        "status": "unknown",
        "details": {},
    }

    if check_port("127.0.0.1", MYSQL_PORT):
        item["details"]["port"] = f"{MYSQL_PORT} (开放)"
    else:
        item["status"] = "error"
        item["details"]["port"] = f"{MYSQL_PORT} (未开放)"
        item["details"]["suggestion"] = "启动 MySQL 服务: net start MySQL84"
        status["items"].append(item)
        return

    # 方式1：通过 venv 中的 Python pymysql 直连（避免 mysql.exe 认证阻塞）
    python_check = os.path.join(BACKEND_DIR, "venv", "Scripts", "python.exe")
    if os.path.exists(python_check):
        try:
            result = subprocess.run(
                [python_check, "-X", "utf8", "-c",
                 "import pymysql; "
                 "c=pymysql.connect(host='127.0.0.1',user='root',password='',"
                 "database='testhub',connect_timeout=5); "
                 "cur=c.cursor(); "
                 "cur.execute('SELECT COUNT(*) FROM information_schema.tables "
                 "WHERE table_schema=%s',('testhub',)); "
                 "print(cur.fetchone()[0]); "
                 "c.close()"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                table_count = result.stdout.strip().split("\n")[-1]
                item["status"] = "ok"
                item["details"]["connection"] = "正常"
                item["details"]["database"] = "testhub"
                item["details"]["tables"] = table_count
            elif "Access denied" in result.stderr:
                item["status"] = "warn"
                item["details"]["connection"] = "认证失败 (密码可能已变更)"
            else:
                item["status"] = "warn"
                item["details"]["connection"] = f"Python 查询异常: {(result.stderr or result.stdout).strip()[:80]}"
        except subprocess.TimeoutExpired:
            item["status"] = "warn"
            item["details"]["connection"] = "Python 连接超时 (10s)"
        except Exception as e:
            item["status"] = "warn"
            item["details"]["connection"] = f"Python 直连失败: {e}"
    else:
        # 回退：仅报告端口开放
        item["status"] = "ok"
        item["details"]["connection"] = "端口开放 (venv 不存在, 跳过数据库查询)"

    status["items"].append(item)


def check_redis(status):
    """检查 Redis 服务"""
    item = {
        "name": "Redis",
        "status": "unknown",
        "details": {},
    }

    if not check_port("127.0.0.1", REDIS_PORT):
        item["status"] = "error"
        item["details"]["port"] = f"{REDIS_PORT} (未开放)"
        item["details"]["suggestion"] = f"启动 Redis: net start Redis"
        status["items"].append(item)
        return

    item["details"]["port"] = f"{REDIS_PORT} (开放)"

    if os.path.exists(REDIS_CLI):
        try:
            result = subprocess.run(
                [REDIS_CLI, "-p", str(REDIS_PORT), "ping"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5
            )
            if "PONG" in result.stdout:
                item["status"] = "ok"
                item["details"]["ping"] = "PONG"
            else:
                item["status"] = "warn"
                item["details"]["ping"] = f"异常响应: {result.stdout.strip()}"
        except Exception:
            item["status"] = "warn"
            item["details"]["ping"] = "无法执行 ping"
    else:
        item["status"] = "ok"
        item["details"]["ping"] = "端口开放"

    if os.path.exists(REDIS_CLI):
        try:
            result = subprocess.run(
                [REDIS_CLI, "-p", str(REDIS_PORT), "info", "server"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5
            )
            for line in result.stdout.splitlines():
                if line.startswith("redis_version:"):
                    item["details"]["version"] = line.split(":", 1)[1].strip()
                if line.startswith("uptime_in_days:"):
                    item["details"]["uptime_days"] = line.split(":", 1)[1].strip()
        except Exception:
            pass

    status["items"].append(item)


def check_neo4j(status):
    """检查 Neo4j 图数据库服务"""
    item = {
        "name": "Neo4j",
        "status": "unknown",
        "details": {},
    }

    # 检查 Bolt 端口（Neo4j 主连接端口）
    if not check_port("127.0.0.1", NEO4J_BOLT_PORT):
        item["status"] = "error"
        item["details"]["bolt_port"] = f"{NEO4J_BOLT_PORT} (未开放)"
        item["details"]["suggestion"] = f"启动 Neo4j: E:\\testhub_platform\\scripts\\start_neo4j.bat"
        status["items"].append(item)
        return

    item["details"]["bolt_port"] = f"{NEO4J_BOLT_PORT} (开放)"

    # 检查 HTTP 端口
    if check_port("127.0.0.1", NEO4J_HTTP_PORT):
        item["details"]["http_port"] = f"{NEO4J_HTTP_PORT} (开放)"
        item["details"]["browser_url"] = f"http://localhost:{NEO4J_HTTP_PORT}/"
    else:
        item["details"]["http_port"] = f"{NEO4J_HTTP_PORT} (未开放)"

    item["status"] = "ok"
    item["details"]["username"] = "neo4j"
    item["details"]["password"] = "testhub123"

    status["items"].append(item)


def check_backend(status):
    """检查后端服务"""
    item = {
        "name": "后端 API (Django)",
        "status": "unknown",
        "details": {},
    }

    if not check_port("127.0.0.1", BACKEND_PORT):
        item["status"] = "error"
        item["details"]["port"] = f"{BACKEND_PORT} (未开放)"
        item["details"]["suggestion"] = (
            f"启动后端: cd {BACKEND_DIR} && "
            f"{VENV_PYTHON} -m uvicorn backend.asgi:application "
            f"--host 0.0.0.0 --port {BACKEND_PORT}"
        )
        status["items"].append(item)
        return

    item["details"]["port"] = f"{BACKEND_PORT} (开放)"
    pid = find_pid_on_port(BACKEND_PORT)
    if pid:
        item["details"]["pid"] = pid

    try:
        import urllib.request
        resp = urllib.request.urlopen(
            f"http://localhost:{BACKEND_PORT}/api/docs/", timeout=30
        )
        if resp.status == 200:
            item["status"] = "ok"
            item["details"]["api_docs"] = "可访问"
            item["details"]["url"] = f"http://localhost:{BACKEND_PORT}/api/docs/"
        else:
            item["status"] = "warn"
            item["details"]["api_docs"] = f"HTTP {resp.status}"
    except Exception as e:
        item["status"] = "warn"
        item["details"]["api_docs"] = f"无响应: {str(e)[:60]}"

    status["items"].append(item)


def check_qcluster(status):
    """检查 Django-Q2 任务队列"""
    item = {
        "name": "Django-Q2 任务队列",
        "status": "unknown",
        "details": {},
    }

    try:
        result = subprocess.run(
            ["wmic", "process", "where",
             "CommandLine like '%qcluster%' and ExecutablePath like '%venv%'",
             "get", "ProcessId,CommandLine"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10
        )
        if "qcluster" in result.stdout.lower():
            item["status"] = "ok"
            item["details"]["status"] = "运行中"
            for line in result.stdout.splitlines():
                line = line.strip()
                if line and line.isdigit():
                    item["details"]["pid"] = int(line)
                    break
        else:
            result2 = subprocess.run(
                ["tasklist"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5
            )
            python_count = sum(1 for l in result2.stdout.splitlines() if "python" in l.lower())
            if python_count >= 2 and check_port("127.0.0.1", BACKEND_PORT):
                item["status"] = "ok"
                item["details"]["status"] = "假设运行中 (后端正常, 检测到多个 Python 进程)"
            else:
                item["status"] = "warn"
                item["details"]["status"] = "未检测到 qcluster 进程"
                item["details"]["suggestion"] = f"启动: cd {BACKEND_DIR} && {VENV_PYTHON} -m manage qcluster"
    except Exception as e:
        item["status"] = "unknown"
        item["details"]["status"] = f"检测失败: {e}"

    status["items"].append(item)


def check_frontend(status):
    """检查前端服务"""
    item = {
        "name": "前端 (Vite)",
        "status": "unknown",
        "details": {},
    }

    found_port = None
    for port in range(FRONTEND_PORT, FRONTEND_PORT + 5):
        if check_port("127.0.0.1", port):
            found_port = port
            break

    if found_port is None:
        item["status"] = "error"
        item["details"]["port"] = f"未检测到前端服务 (扫描 {FRONTEND_PORT}-{FRONTEND_PORT+4})"
        item["details"]["suggestion"] = f"启动前端: cd {os.path.join(PROJECT_ROOT, 'frontend')} && npm run dev"
        status["items"].append(item)
        return

    item["details"]["port"] = f"{found_port} (开放)"
    item["details"]["url"] = f"http://localhost:{found_port}/"
    pid = find_pid_on_port(found_port)
    if pid:
        item["details"]["pid"] = pid

    try:
        import urllib.request
        resp = urllib.request.urlopen(f"http://localhost:{found_port}/", timeout=10)
        if resp.status == 200:
            item["status"] = "ok"
            item["details"]["http"] = "可访问"
        else:
            item["status"] = "warn"
            item["details"]["http"] = f"HTTP {resp.status}"
    except Exception as e:
        item["status"] = "warn"
        item["details"]["http"] = f"无响应: {str(e)[:60]}"

    status["items"].append(item)


def check_database_migrations(status):
    """检查数据库迁移状态"""
    item = {
        "name": "数据库迁移",
        "status": "unknown",
        "details": {},
    }

    if not os.path.exists(VENV_PYTHON):
        item["status"] = "error"
        item["details"]["error"] = f"Python venv 不存在: {VENV_PYTHON}"
        status["items"].append(item)
        return

    try:
        result = subprocess.run(
            [VENV_PYTHON, "-X", "utf8", "-c",
             "import os,sys\n"
             "os.environ.setdefault('DJANGO_SETTINGS_MODULE','backend.dev_settings')\n"
             "sys.path.insert(0,'.')\n"
             "import django; django.setup()\n"
             "from django.db.migrations.executor import MigrationExecutor\n"
             "from django.db import connection\n"
             "from django.db.migrations.recorder import MigrationRecorder\n"
             "recorder=MigrationRecorder(connection)\n"
             "applied=len(recorder.applied_migrations())\n"
             "executor=MigrationExecutor(connection)\n"
             "pending=len(executor.migration_plan(executor.loader.graph.leaf_nodes()))\n"
             "print(f'{applied}|{pending}')"],
            cwd=BACKEND_DIR,
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60
        )
        output = result.stdout.strip().split("\n")[-1] if result.stdout else ""
        if "|" in output:
            parts = output.split("|")
            applied = parts[0].strip()
            pending = parts[1].strip()
            item["details"]["applied"] = applied
            item["details"]["pending"] = pending
            if pending == "0":
                item["status"] = "ok"
            else:
                item["status"] = "warn"
                item["details"]["suggestion"] = "运行: python safe_migrate.py && python manage.py migrate --run-syncdb"
        else:
            item["status"] = "unknown"
            item["details"]["output"] = output[:100]
    except subprocess.TimeoutExpired:
        item["status"] = "warn"
        item["details"]["error"] = "检查超时"
    except Exception as e:
        item["status"] = "warn"
        item["details"]["error"] = str(e)[:100]

    status["items"].append(item)


def check_login(status):
    """检查超级用户登录"""
    item = {
        "name": "超级用户登录",
        "status": "unknown",
        "details": {},
    }

    if not check_port("127.0.0.1", BACKEND_PORT):
        item["status"] = "skip"
        item["details"]["reason"] = "后端未运行，跳过登录检查"
        status["items"].append(item)
        return

    try:
        import urllib.request
        data = json.dumps({
            "username": "admin",
            "password": "admin123456"
        }).encode("utf-8")
        req = urllib.request.Request(
            f"http://localhost:{BACKEND_PORT}/api/auth/login/",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        resp = urllib.request.urlopen(req, timeout=30)
        resp_data = json.loads(resp.read().decode("utf-8"))
        if "access" in resp_data:
            item["status"] = "ok"
            item["details"]["login"] = "成功"
            item["details"]["token_type"] = "JWT"
        else:
            item["status"] = "error"
            item["details"]["login"] = "失败"
            item["details"]["response"] = str(resp_data)[:100]
    except urllib.error.HTTPError as e:
        item["status"] = "error"
        item["details"]["login"] = f"HTTP {e.code}"
        try:
            body = e.read().decode("utf-8")[:200]
            item["details"]["response"] = body
        except Exception:
            pass
    except Exception as e:
        item["status"] = "error"
        item["details"]["login"] = f"异常: {str(e)[:80]}"

    status["items"].append(item)


def check_config(status):
    """检查配置文件"""
    item = {
        "name": "配置文件",
        "status": "unknown",
        "details": {},
    }

    if os.path.exists(CONFIG_FILE):
        item["details"]["config.yaml"] = "存在"
        try:
            import yaml
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            if config.get("database", {}).get("name"):
                item["details"]["db_name"] = config["database"]["name"]
            if config.get("server", {}).get("backend_port"):
                item["details"]["backend_port"] = config["server"]["backend_port"]
        except Exception as e:
            item["details"]["config.yaml"] = f"解析失败: {e}"
    else:
        item["details"]["config.yaml"] = "不存在"

    env_file = os.path.join(PROJECT_ROOT, "frontend", ".env")
    if os.path.exists(env_file):
        item["details"]["frontend/.env"] = "存在"
    else:
        item["details"]["frontend/.env"] = "不存在 (运行 npm run dev 自动生成)"

    if os.path.exists(VENV_PYTHON):
        item["details"]["python_venv"] = "存在"
    else:
        item["details"]["python_venv"] = "不存在"

    node_modules = os.path.join(PROJECT_ROOT, "frontend", "node_modules")
    if os.path.exists(node_modules):
        item["details"]["node_modules"] = "存在"
    else:
        item["details"]["node_modules"] = "不存在 (运行 npm install)"

    has_issues = any(
        isinstance(v, str) and ("不存在" in v or "失败" in v)
        for v in item["details"].values()
    )
    item["status"] = "warn" if has_issues else "ok"

    status["items"].append(item)


# ============================================================
# 输出格式化
# ============================================================

def format_status(s):
    """将状态转为显示符号"""
    if _ANSI_SUPPORTED:
        return {
            "ok": f"{Color.GREEN}{Color.SYM_OK} 正常{Color.RESET}",
            "warn": f"{Color.YELLOW}{Color.SYM_WARN} 警告{Color.RESET}",
            "error": f"{Color.RED}{Color.SYM_FAIL} 异常{Color.RESET}",
            "skip": f"{Color.DIM}{Color.SYM_SKIP} 跳过{Color.RESET}",
            "unknown": f"{Color.CYAN}? 未知{Color.RESET}",
        }.get(s, s)
    else:
        return {
            "ok": f"{Color.SYM_OK} 正常",
            "warn": f"{Color.SYM_WARN} 警告",
            "error": f"{Color.SYM_FAIL} 异常",
            "skip": f"{Color.SYM_SKIP} 跳过",
            "unknown": "? 未知",
        }.get(s, s)


def print_report(status, quiet=False):
    """打印检查报告"""
    print(flush=True)
    print(f"{Color.BOLD}{'='*55}{Color.RESET}", flush=True)
    print(f"{Color.BOLD}  TestHub 服务状态检查报告{Color.RESET}", flush=True)
    print(f"{Color.BOLD}{'='*55}{Color.RESET}", flush=True)
    print(f"  检查时间: {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print(f"  项目目录: {PROJECT_ROOT}", flush=True)
    print(flush=True)

    for item in status["items"]:
        name = item["name"]
        s = item["status"]
        details = item.get("details", {})

        if quiet and s == "ok":
            continue

        print(f"  {Color.BOLD}{name}{Color.RESET}", flush=True)
        print(f"    状态: {format_status(s)}", flush=True)
        for key, value in details.items():
            print(f"    {Color.DIM}{key}:{Color.RESET} {value}", flush=True)
        suggestion = item.get("details", {}).get("suggestion")
        if suggestion and s != "ok":
            print(f"    {Color.CYAN}建议:{Color.RESET} {suggestion}", flush=True)
        print(flush=True)

    # 汇总
    total = len(status["items"])
    ok_count = sum(1 for i in status["items"] if i["status"] == "ok")
    warn_count = sum(1 for i in status["items"] if i["status"] == "warn")
    error_count = sum(1 for i in status["items"] if i["status"] == "error")
    skip_count = sum(1 for i in status["items"] if i["status"] == "skip")

    print(f"  {Color.BOLD}{'─'*50}{Color.RESET}", flush=True)
    print(f"  汇总: {total} 项 | {Color.GREEN}{ok_count} 正常{Color.RESET} | "
          f"{Color.YELLOW}{warn_count} 警告{Color.RESET} | "
          f"{Color.RED}{error_count} 异常{Color.RESET} | "
          f"{Color.DIM}{skip_count} 跳过{Color.RESET}", flush=True)

    # 访问信息
    if ok_count > 0:
        print(f"\n  {Color.BOLD}访问信息:{Color.RESET}", flush=True)
        for item in status["items"]:
            url = item.get("details", {}).get("url")
            if url:
                print(f"    {item['name']}: {url}", flush=True)

    print(f"\n  {Color.BOLD}{'='*55}{Color.RESET}", flush=True)

    return error_count == 0


# ============================================================
# 主函数
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="TestHub 服务状态检查")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    parser.add_argument("--quiet", action="store_true", help="仅输出异常项")
    args = parser.parse_args()

    # 读取配置
    try:
        import yaml
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        if config.get("server"):
            global BACKEND_PORT, FRONTEND_PORT
            BACKEND_PORT = config["server"].get("backend_port", BACKEND_PORT)
            FRONTEND_PORT = config["server"].get("frontend_port", FRONTEND_PORT)
    except Exception:
        pass

    # 执行所有检查
    status = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "project_root": PROJECT_ROOT,
        "items": [],
    }

    check_mysql(status)
    check_redis(status)
    check_neo4j(status)
    check_backend(status)
    check_qcluster(status)
    check_frontend(status)
    check_database_migrations(status)
    check_login(status)
    check_config(status)

    if args.json:
        print(json.dumps(status, ensure_ascii=False, indent=2), flush=True)
    else:
        ok = print_report(status, quiet=args.quiet)
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
