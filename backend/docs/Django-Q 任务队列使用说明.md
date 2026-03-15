# Django-Q 任务队列使用说明

## 命令执行说明

### 1. `python manage.py runworker tasks` 命令的作用
- **作用**：启动Django-Q的工作进程，用于处理异步任务
- **必要性**：是的，每次启动系统时都需要执行此命令
- **监控信息**：执行后，可以在Admin后台的"任务管理"中查看任务执行状态

### 2. 为什么需要每次启动都执行？
Django-Q使用Redis作为消息队列，工作进程负责：
- 从Redis队列中获取待执行的任务
- 执行任务并记录结果
- 处理任务失败和重试
- 更新任务状态到数据库

### 3. 生产环境建议

#### 方案1：使用Supervisor管理（推荐）
```ini
[program:testhub_worker]
command=/path/to/venv/bin/python manage.py runworker tasks
directory=/path/to/testhub/backend
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/testhub_worker.log
```

#### 方案2：使用Systemd服务
```ini
[Unit]
Description=TestHub Django-Q Worker
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/testhub/backend
ExecStart=/path/to/venv/bin/python manage.py runworker tasks
Restart=always

[Install]
WantedBy=multi-user.target
```

#### 方案3：使用Docker Compose

```yaml
version: '3'
services:
  worker:
    build: ../../docs
    command: python manage.py runworker tasks
    depends_on:
      - redis
      - db
    restart: always
```

### 4. 开发环境建议

#### 使用后台运行
```bash
# Windows PowerShell
Start-Process -NoNewWindow python -ArgumentList "manage.py runworker tasks"

# Linux/Mac
nohup python manage.py runworker tasks > worker.log 2>&1 &
```

#### 使用多终端
- 终端1：运行开发服务器 `python manage.py runserver`
- 终端2：运行工作进程 `python manage.py runworker tasks`

### 5. 监控信息查看位置

#### Admin后台监控
访问 http://127.0.0.1:8000/admin/ 可以查看：

**任务管理模块**：
- **任务管理**：查看所有异步任务的执行状态
  - 任务ID、名称、函数、分组
  - 开始时间、结束时间、执行状态
  - 成功/失败状态标识

- **定时任务**：查看定时任务的调度情况
  - 任务名称、调度类型、下次运行时间
  - 上次运行时间、成功次数
  - 任务状态和配置信息

**通知日志模块**：
- **API测试通知日志**：查看API测试的通知发送记录
- **UI自动化通知日志**：查看UI自动化的通知发送记录
- **APP自动化通知日志**：查看APP自动化的通知发送记录

**核心模块**：
- **请求性能日志**：查看HTTP请求性能
- **性能统计**：查看每日性能汇总

### 6. 常用命令

```bash
# 启动工作进程
python manage.py runworker tasks

# 启动指定数量的工作进程
python manage.py runworker tasks --workers=4

# 查看工作进程状态
python manage.py qcluster

# 停止工作进程
# 按 Ctrl+C 或使用 kill 命令
```

### 7. 故障排查

#### 工作进程未启动
- 检查Redis是否运行：`redis-cli ping`
- 检查Redis配置是否正确
- 查看日志文件获取错误信息

#### 任务未执行
- 确认工作进程正在运行
- 检查任务是否正确入队
- 查看Admin后台的任务状态

#### 性能问题
- 调整工作进程数量
- 优化任务执行逻辑
- 检查Redis连接配置

### 8. 配置优化

当前配置（settings.py）：
```python
Q_CLUSTER = {
    'name': 'testhub',
    'workers': 1,           # 工作进程数，可根据服务器配置调整
    'timeout': 90,          # 任务超时时间（秒）
    'retry': 120,           # 重试时间（秒）
    'queue_limit': 50,      # 队列限制
    'bulk': 10,             # 批量处理数量
    'orm': 'default',       # 数据库配置
    'save_limit': 250,      # 保存限制
    'cpu_affinity': 1,      # CPU 亲和性
    'label': '任务队列',     # Admin 菜单显示名称
    'redis': REDIS_URL,     # Redis 配置
    'sync': False,          # False异步模式，True同步模式
}
```

优化建议：
- 生产环境增加 `workers` 数量（建议2-4）
- 根据任务复杂度调整 `timeout`
- 高并发场景增加 `queue_limit`
- 监控Redis内存使用情况