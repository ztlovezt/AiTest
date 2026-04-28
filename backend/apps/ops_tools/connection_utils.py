from __future__ import annotations

import contextlib
import posixpath
import select
import shlex
import socketserver
import stat
import threading
import time
from contextlib import contextmanager
from pathlib import Path

import paramiko
import pymongo
import pymysql
import redis


SSH_TIMEOUT = 5
SERVICE_TIMEOUT = 5
SSH_CACHE_TTL = 30


class _CachedSSHClient:
    """缓存短时可复用的 SSH 客户端，减少频繁握手带来的耗时。"""

    def __init__(self, host: str, port: int, username: str, password: str):
        self.host = host
        self.port = int(port or 22)
        self.username = username
        self.password = password
        self.client = _create_ssh_client(host, self.port, username, password)
        self.lock = threading.Lock()
        self.use_count = 0
        self.expires_at = time.monotonic() + SSH_CACHE_TTL

    def is_alive(self):
        transport = self.client.get_transport()
        return bool(transport and transport.is_active())

    def refresh(self):
        self.client = _create_ssh_client(self.host, self.port, self.username, self.password)
        self.expires_at = time.monotonic() + SSH_CACHE_TTL

    def close(self):
        with contextlib.suppress(Exception):
            self.client.close()


_SSH_CLIENT_CACHE = {}
_SSH_CACHE_LOCK = threading.Lock()


class _ForwardHandler(socketserver.BaseRequestHandler):
    """通过 paramiko 转发本地端口到远程服务。"""

    def handle(self):
        transport = self.server.ssh_transport
        remote_host = self.server.remote_host
        remote_port = self.server.remote_port
        channel = transport.open_channel(
            "direct-tcpip",
            (remote_host, remote_port),
            self.request.getpeername(),
        )
        if channel is None:
            return

        try:
            while True:
                readable, _, _ = select.select([self.request, channel], [], [], 1)
                if self.request in readable:
                    data = self.request.recv(1024)
                    if not data:
                        break
                    channel.sendall(data)
                if channel in readable:
                    data = channel.recv(1024)
                    if not data:
                        break
                    self.request.sendall(data)
        finally:
            with contextlib.suppress(Exception):
                channel.close()
            with contextlib.suppress(Exception):
                self.request.close()


class _ForwardServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, server_address, handler_class, ssh_transport, remote_host, remote_port):
        self.ssh_transport = ssh_transport
        self.remote_host = remote_host
        self.remote_port = remote_port
        super().__init__(server_address, handler_class)


@contextmanager
def open_ssh_client(host: str, port: int, username: str, password: str):
    """创建 SSH 连接。"""

    client = _create_ssh_client(host, port, username, password)
    try:
        yield client
    finally:
        with contextlib.suppress(Exception):
            client.close()


def _create_ssh_client(host: str, port: int, username: str, password: str):
    """建立新的 SSH 客户端连接。"""

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=host,
        port=int(port or 22),
        username=username,
        password=password,
        timeout=SSH_TIMEOUT,
        banner_timeout=SSH_TIMEOUT,
        auth_timeout=SSH_TIMEOUT,
        look_for_keys=False,
        allow_agent=False,
    )
    return client


def _cleanup_cached_ssh_clients():
    """清理过期且空闲的 SSH 连接，避免长时间占用资源。"""

    now = time.monotonic()
    expired_keys = []
    for key, cached in _SSH_CLIENT_CACHE.items():
        if cached.use_count == 0 and cached.expires_at <= now:
            expired_keys.append(key)

    for key in expired_keys:
        cached = _SSH_CLIENT_CACHE.pop(key, None)
        if cached:
            cached.close()


@contextmanager
def open_cached_ssh_client(host: str, port: int, username: str, password: str):
    """获取一个可短时复用的 SSH 客户端，串行复用以降低重连耗时。"""

    cache_key = (host, int(port or 22), username, password)
    with _SSH_CACHE_LOCK:
        _cleanup_cached_ssh_clients()
        cached = _SSH_CLIENT_CACHE.get(cache_key)
        if cached is None:
            cached = _CachedSSHClient(host, port, username, password)
            _SSH_CLIENT_CACHE[cache_key] = cached
        elif not cached.is_alive():
            cached.close()
            cached.refresh()
        cached.use_count += 1

    cached.lock.acquire()
    try:
        cached.expires_at = time.monotonic() + SSH_CACHE_TTL
        yield cached.client
    finally:
        cached.lock.release()
        with _SSH_CACHE_LOCK:
            cached.use_count = max(0, cached.use_count - 1)
            cached.expires_at = time.monotonic() + SSH_CACHE_TTL
            _cleanup_cached_ssh_clients()


@contextmanager
def forward_local_port(ssh_client: paramiko.SSHClient, remote_host: str, remote_port: int):
    """临时建立本地端口转发。"""

    server = _ForwardServer(
        ("127.0.0.1", 0),
        _ForwardHandler,
        ssh_client.get_transport(),
        remote_host,
        int(remote_port),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        with contextlib.suppress(Exception):
            server.shutdown()
        with contextlib.suppress(Exception):
            server.server_close()
        thread.join(timeout=1)


def build_test_result(success: bool, message: str, detail: dict | None = None):
    return {
        "success": success,
        "message": message,
        "detail": detail or {},
    }


def normalize_service_config(config: dict | None):
    if not isinstance(config, dict):
        return {}
    return config


def validate_remote_path(root: str, relative_path: str):
    """拼接并校验 SSH 根目录下的相对路径。"""

    normalized_root = posixpath.normpath(root or "/")
    normalized_relative = str(relative_path or "").replace("\\", "/").strip("/")
    target = posixpath.normpath(posixpath.join(normalized_root, normalized_relative))
    if target != normalized_root and not target.startswith(normalized_root.rstrip("/") + "/"):
        raise ValueError("访问路径超出目录范围")
    return normalized_relative, target


def resolve_local_path(root: Path, relative_path: str):
    normalized_relative = str(relative_path or "").replace("\\", "/").strip("/")
    target = (root / normalized_relative).resolve(strict=False)
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError("访问路径超出目录范围") from exc
    return normalized_relative, target


def list_local_directory(root: Path, relative_path: str):
    normalized_relative, target = resolve_local_path(root, relative_path)
    if not target.exists():
        raise FileNotFoundError("目录不存在")
    if not target.is_dir():
        raise NotADirectoryError("当前路径不是目录")

    items = []
    for child in sorted(target.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
        stat_info = child.stat()
        child_relative = child.relative_to(root).as_posix()
        items.append(
            {
                "name": child.name,
                "path": child_relative,
                "is_dir": child.is_dir(),
                "size": 0 if child.is_dir() else stat_info.st_size,
                "modified_at": stat_info.st_mtime,
                "extension": "" if child.is_dir() else child.suffix,
            }
        )
    return normalized_relative, items


def list_remote_directory(ssh_client: paramiko.SSHClient, root: str, relative_path: str):
    normalized_relative, target = validate_remote_path(root, relative_path)
    quoted_target = shlex.quote(target)
    command = (
        f"if [ ! -d {quoted_target} ]; then exit 2; fi; "
        f"find {quoted_target} -mindepth 1 -maxdepth 1 "
        "-printf '%f\\t%y\\t%s\\t%T@\\n'"
    )
    _, stdout, stderr = ssh_client.exec_command(command, timeout=SSH_TIMEOUT)
    output = stdout.read().decode("utf-8", errors="ignore")
    error = stderr.read().decode("utf-8", errors="ignore").strip()
    exit_code = stdout.channel.recv_exit_status()

    if exit_code == 0:
        items = []
        normalized_root = root.rstrip("/")
        for line in output.splitlines():
            parts = line.split("\t", 3)
            if len(parts) != 4:
                continue
            name, file_type, size, modified_at = parts
            is_dir = file_type == "d"
            child_path = posixpath.join(target, name)
            child_relative = child_path[len(normalized_root) + 1 :] if child_path != root else ""
            items.append(
                {
                    "name": name,
                    "path": child_relative,
                    "is_dir": is_dir,
                    "size": 0 if is_dir else int(float(size or 0)),
                    "modified_at": int(float(modified_at or 0)),
                    "extension": "" if is_dir else Path(name).suffix,
                }
            )
        items.sort(key=lambda item: (not item["is_dir"], item["name"].lower()))
        return normalized_relative, items

    if exit_code == 2:
        raise FileNotFoundError("目录不存在")

    sftp = ssh_client.open_sftp()
    try:
        attrs = sftp.listdir_attr(target)
    except FileNotFoundError as exc:
        raise FileNotFoundError("目录不存在") from exc
    finally:
        with contextlib.suppress(Exception):
            sftp.close()

    items = []
    for attr in sorted(attrs, key=lambda item: (not stat.S_ISDIR(item.st_mode), item.filename.lower())):
        child_path = posixpath.join(target, attr.filename)
        child_relative = child_path[len(root.rstrip("/")) + 1 :] if child_path != root else ""
        items.append(
            {
                "name": attr.filename,
                "path": child_relative,
                "is_dir": stat.S_ISDIR(attr.st_mode),
                "size": 0 if stat.S_ISDIR(attr.st_mode) else attr.st_size,
                "modified_at": attr.st_mtime,
                "extension": "" if stat.S_ISDIR(attr.st_mode) else Path(attr.filename).suffix,
            }
        )
    return normalized_relative, items


def tail_local_file(root: Path, relative_path: str, lines: int):
    normalized_relative, target = resolve_local_path(root, relative_path)
    if not target.exists():
        raise FileNotFoundError("文件不存在")
    if not target.is_file():
        raise IsADirectoryError("当前路径不是文件")

    buffer = _read_last_lines(target, lines)

    stat_info = target.stat()
    return {
        "path": normalized_relative,
        "name": target.name,
        "size": stat_info.st_size,
        "modified_at": stat_info.st_mtime,
        "lines": buffer,
        "line_count": len(buffer),
        "encoding": "utf-8",
    }


def tail_remote_file(ssh_client: paramiko.SSHClient, root: str, relative_path: str, lines: int):
    normalized_relative, target = validate_remote_path(root, relative_path)
    quoted_target = shlex.quote(target)
    command = (
        f"if [ ! -f {quoted_target} ]; then exit 2; fi; "
        f"stat -c '__OPS_META__%s\\t%Y' -- {quoted_target}; "
        f"tail -n {int(lines)} -- {quoted_target}"
    )
    _, stdout, stderr = ssh_client.exec_command(command, timeout=SSH_TIMEOUT)
    output = stdout.read().decode("utf-8", errors="ignore")
    error = stderr.read().decode("utf-8", errors="ignore").strip()
    exit_code = stdout.channel.recv_exit_status()
    if exit_code == 2:
        raise FileNotFoundError("文件不存在")
    if exit_code != 0:
        raise FileNotFoundError(error or "读取远程文件失败")

    output_lines = output.splitlines()
    size = 0
    modified_at = 0
    content_lines = output_lines
    if output_lines and output_lines[0].startswith("__OPS_META__"):
        meta = output_lines[0].replace("__OPS_META__", "", 1).split("\t", 1)
        if len(meta) == 2:
            size = int(meta[0] or 0)
            modified_at = int(meta[1] or 0)
        content_lines = output_lines[1:]

    return {
        "path": normalized_relative,
        "name": Path(target).name,
        "size": size,
        "modified_at": modified_at,
        "lines": content_lines,
        "line_count": len(content_lines),
        "encoding": "utf-8",
    }


def _read_last_lines(target: Path, lines: int):
    """从文件尾部按块逆向读取，避免大文件全量扫描。"""

    if lines <= 0:
        return []

    block_size = 4096
    remaining = lines + 1
    chunks = []

    with target.open("rb") as file_obj:
        file_obj.seek(0, 2)
        file_size = file_obj.tell()
        position = file_size

        while position > 0 and remaining > 0:
            read_size = min(block_size, position)
            position -= read_size
            file_obj.seek(position)
            chunk = file_obj.read(read_size)
            chunks.append(chunk)
            remaining -= chunk.count(b"\n")

    content = b"".join(reversed(chunks)).decode("utf-8", errors="ignore")
    return content.splitlines()[-lines:]


def test_ssh_connection(host: str, port: int, username: str, password: str):
    if not host or not username:
        return build_test_result(False, "未配置 SSH 主机或用户名")
    try:
        with open_cached_ssh_client(host, port, username, password):
            return build_test_result(True, "SSH 连接成功")
    except Exception as exc:
        return build_test_result(False, f"SSH 连接失败: {exc}")


def _service_connect_params(config: dict):
    return {
        "host": config.get("host") or "127.0.0.1",
        "port": int(config.get("port") or 0),
        "username": config.get("username") or "",
        "password": config.get("password") or "",
        "database": config.get("database") or "",
        "db": int(config.get("db") or 0),
        "auth_database": config.get("auth_database") or config.get("database") or "admin",
        "collection": config.get("collection") or "",
        "use_ssh": bool(config.get("use_ssh")),
        "enabled": bool(config.get("enabled", True)),
    }


def test_mysql_connection(config: dict, ssh_config: dict | None = None):
    config = _service_connect_params(config)
    if not config["enabled"]:
        return build_test_result(False, "MySQL 未启用", {"skipped": True})
    if not config["port"] or not config["username"]:
        return build_test_result(False, "MySQL 配置不完整")

    def _connect(host: str, port: int):
        connection = pymysql.connect(
            host=host,
            port=port,
            user=config["username"],
            password=config["password"],
            database=config["database"] or None,
            connect_timeout=SERVICE_TIMEOUT,
            read_timeout=SERVICE_TIMEOUT,
            write_timeout=SERVICE_TIMEOUT,
            charset="utf8mb4",
        )
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        finally:
            connection.close()

    try:
        if config["use_ssh"]:
            with open_ssh_client(**ssh_config) as ssh_client, forward_local_port(
                ssh_client,
                config["host"],
                config["port"],
            ) as local_port:
                _connect("127.0.0.1", local_port)
        else:
            _connect(config["host"], config["port"])
        return build_test_result(True, "MySQL 连接成功")
    except Exception as exc:
        return build_test_result(False, f"MySQL 连接失败: {exc}")


def test_redis_connection(config: dict, ssh_config: dict | None = None):
    config = _service_connect_params(config)
    if not config["enabled"]:
        return build_test_result(False, "Redis 未启用", {"skipped": True})
    if not config["port"]:
        return build_test_result(False, "Redis 配置不完整")

    def _connect(host: str, port: int):
        client = redis.Redis(
            host=host,
            port=port,
            username=config["username"] or None,
            password=config["password"] or None,
            db=config["db"],
            socket_connect_timeout=SERVICE_TIMEOUT,
            socket_timeout=SERVICE_TIMEOUT,
            decode_responses=True,
        )
        client.ping()

    try:
        if config["use_ssh"]:
            with open_ssh_client(**ssh_config) as ssh_client, forward_local_port(
                ssh_client,
                config["host"],
                config["port"],
            ) as local_port:
                _connect("127.0.0.1", local_port)
        else:
            _connect(config["host"], config["port"])
        return build_test_result(True, "Redis 连接成功")
    except Exception as exc:
        return build_test_result(False, f"Redis 连接失败: {exc}")


def test_mongo_connection(config: dict, ssh_config: dict | None = None):
    config = _service_connect_params(config)
    if not config["enabled"]:
        return build_test_result(False, "MongoDB 未启用", {"skipped": True})
    if not config["port"]:
        return build_test_result(False, "MongoDB 配置不完整")

    def _connect(host: str, port: int):
        client = pymongo.MongoClient(
            host=host,
            port=port,
            username=config["username"] or None,
            password=config["password"] or None,
            authSource=config["auth_database"] or None,
            serverSelectionTimeoutMS=SERVICE_TIMEOUT * 1000,
            connectTimeoutMS=SERVICE_TIMEOUT * 1000,
            socketTimeoutMS=SERVICE_TIMEOUT * 1000,
        )
        try:
            client.admin.command("ping")
        finally:
            client.close()

    try:
        if config["use_ssh"]:
            with open_ssh_client(**ssh_config) as ssh_client, forward_local_port(
                ssh_client,
                config["host"],
                config["port"],
            ) as local_port:
                _connect("127.0.0.1", local_port)
        else:
            _connect(config["host"], config["port"])
        return build_test_result(True, "MongoDB 连接成功")
    except Exception as exc:
        return build_test_result(False, f"MongoDB 连接失败: {exc}")
