# Celery 替换为 Django-Q2 迁移指南

## 概述

本文档说明如何将项目中的 Celery 异步任务系统替换为 Django-Q2，以减少第三方依赖。

## 变更原因

- **减少依赖**: Celery 依赖较多，配置复杂
- **简化架构**: Django-Q2 更轻量，配置更简单
- **功能满足**: Django-Q2 提供的功能已满足项目需求

## 主要变更

### 1. 依赖变更

**移除**:
```txt
celery==5.6.2
```

**新增**:
```txt
django-q2>=1.6.0
```

### 2. 配置变更

#### settings.py

**移除**:
```python
# Celery配置
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
```

**新增**:
```python
# Django-Q2 配置（替换 Celery）
Q_CLUSTER = {
    'name': 'testhub',
    'workers': 4,
    'timeout': 90,
    'retry': 120,
    'queue_limit': 50,
    'bulk': 10,
    'orm': 'default',
    'save_limit': 250,
    'cpu_affinity': 1,
    'label': 'Django Q',
    'redis': REDIS_URL,
    'sync': False,  # 异步模式
}
```

**添加应用**:
```python
INSTALLED_APPS = [
    # ...
    'django_q2',  # 替换 Celery 为 Django-Q2
]
```

### 3. 代码变更

#### 任务定义

**原代码 (tasks.py)**:
```python
from celery import shared_task

@shared_task
def execute_app_test_task(execution_id, package_name=None, scheduled_task_id=None):
    # 任务逻辑
    pass
```

**新代码 (tasks_async.py)**:
```python
from django_q2 import task

@task
def execute_app_test_task(execution_id, package_name=None, scheduled_task_id=None):
    # 任务逻辑
    pass
```

#### 任务调用

**原代码**:
```python
from ..tasks import execute_app_test_task

celery_task = execute_app_test_task.delay(
    execution.id,
    package_name=package_name,
    scheduled_task_id=task.id,
)
execution.task_id = celery_task.id
```

**新代码**:
```python
from ..tasks_async import execute_app_test_task

async_task = execute_app_test_task.async(
    execution.id,
    package_name=package_name,
    scheduled_task_id=task.id,
)
execution.task_id = async_task.id
```

#### 任务终止

**原代码**:
```python
from celery import current_app
current_app.control.revoke(execution.task_id, terminate=True, signal='SIGTERM')
```

**新代码**:
```python
from django_q2.models import Task
task = Task.objects.get(id=execution.task_id)
task.stop()
```

### 4. 启动方式变更

#### 原启动方式 (Celery)
```bash
# 启动 Celery Worker
celery -A backend worker -l info
```

#### 新启动方式 (Django-Q2)
```bash
# 启动 Django-Q2 Cluster
python manage.py qcluster

# 或者使用自定义配置
python manage.py qcluster --conf=backend.settings
```

### 5. 数据库迁移

Django-Q2 需要创建自己的数据表：

```bash
# 创建 Django-Q2 数据表
python manage.py migrate django_q2
```

## 迁移步骤

### 1. 备份现有数据

```bash
# 备份数据库
mysqldump -u root -p testhub > testhub_backup.sql
```

### 2. 安装新依赖

```bash
cd backend
pip uninstall celery
pip install django-q2>=1.6.0
```

### 3. 更新代码

按照上述变更更新配置文件和代码文件。

### 4. 运行数据库迁移

```bash
python manage.py migrate django_q2
```

### 5. 重启服务

```bash
# 停止旧的 Celery Worker
# 启动新的 Django-Q2 Cluster
python manage.py qcluster
```

### 6. 验证功能

- 测试 APP 自动化测试任务执行
- 验证定时任务功能
- 检查任务状态更新
- 确认 WebSocket 通知正常

## API 差异对比

| 功能 | Celery | Django-Q2 |
|------|---------|------------|
| 任务装饰器 | `@shared_task` | `@task` |
| 异步调用 | `task.delay()` | `task.async()` |
| 任务结果 | `AsyncResult` | `Task` 模型 |
| 任务终止 | `control.revoke()` | `task.stop()` |
| 任务监控 | Flower | Django Admin 内置 |
| 定时任务 | Celery Beat | Django-Q2 Scheduler |

## 注意事项

1. **任务ID**: Django-Q2 的任务ID格式与 Celery 不同，但都是字符串类型，数据库字段无需修改

2. **任务结果**: Django-Q2 使用 Django ORM 存储任务结果，可以在 Django Admin 中查看

3. **性能调优**: 根据服务器配置调整 `Q_CLUSTER` 中的 `workers` 参数

4. **Redis 连接**: 确保 Redis 服务正常运行，Django-Q2 依赖 Redis 作为消息队列

5. **向后兼容**: 旧的 `tasks.py` 文件保留，新代码使用 `tasks_async.py`

## 回滚方案

如果需要回滚到 Celery：

1. 恢复 `requirements.txt` 中的 Celery 依赖
2. 恢复 `settings.py` 中的 Celery 配置
3. 恢复代码中的任务导入和调用方式
4. 卸载 Django-Q2: `pip uninstall django-q2`
5. 重新安装 Celery: `pip install celery==5.6.2`
6. 启动 Celery Worker: `celery -A backend worker -l info`

## 参考文档

- [Django-Q2 官方文档](https://django-q2.readthedocs.io/)
- [Celery 官方文档](https://docs.celeryproject.org/)
- [项目 README](../../README.md)

## 更新日志

- 2026-02-27: 完成 Celery 到 Django-Q2 的迁移
