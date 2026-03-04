# Django-Q 定时任务管理指南

## 概述

本文档说明如何在 TestHub 平台中使用 Django-Q 进行定时任务管理，包括任务创建、执行、暂停/恢复、统计等功能。

## Django-Q 简介

### 什么是 Django-Q

Django-Q 是一个轻量级的异步任务队列和定时任务调度系统，用于替代 Celery。它具有以下特点：

- **轻量级**: 依赖少，配置简单
- **内置管理**: 集成 Django Admin，无需额外监控工具
- **定时任务**: 内置强大的定时任务调度功能
- **异步执行**: 支持异步任务执行和结果追踪

### 与 Celery 的对比

| 特性 | Celery | Django-Q |
|------|---------|----------|
| 依赖 | Redis + RabbitMQ | Redis |
| 配置复杂度 | 高 | 低 |
| 监控工具 | Flower | Django Admin 内置 |
| 定时任务 | Celery Beat | 内置 Scheduler |
| 任务队列 | 支持 | 支持 |
| 任务追踪 | Result Backend | ORM 存储 |

## 任务调度机制

### Django-Q 调度器工作原理

Django-Q 的调度器会定期检查数据库中的 `Schedule` 表，查找满足条件的任务并执行：

```python
# 调度器查询条件
Schedule.objects.filter(
    next_run__lt=timezone.now()  # 下次执行时间小于当前时间
).exclude(repeats=0)  # 排除已完成的任务
```

### 关键字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | String | 任务名称 |
| `func` | String | 要执行的函数路径（如 `apps.scheduler.task_executor.execute_task`） |
| `args` | String | 位置参数（JSON 字符串） |
| `kwargs` | String | 关键字参数（JSON 字符串） |
| `schedule_type` | String | 调度类型（O/I/H/D/W/BW/M/BM/Q/Y/C） |
| `minutes` | Integer | 间隔分钟数（仅 MINUTES 类型） |
| `repeats` | Integer | 重复次数（-1 表示无限次） |
| `next_run` | DateTime | 下次执行时间 |
| `cron` | String | Cron 表达式（仅 CRON 类型） |
| `task` | String | 当前执行的任务ID |

### 调度类型

| 代码 | 类型 | 说明 |
|------|------|------|
| O | Once | 单次执行 |
| I | Minutes | 每N分钟执行一次 |
| H | Hourly | 每小时执行一次 |
| D | Daily | 每天执行一次 |
| W | Weekly | 每周执行一次 |
| BW | Biweekly | 每两周执行一次 |
| M | Monthly | 每月执行一次 |
| BM | Bimonthly | 每两月执行一次 |
| Q | Quarterly | 每季度执行一次 |
| Y | Yearly | 每年执行一次 |
| C | Cron | 使用 Cron 表达式 |

## 任务管理

### 创建定时任务

#### 方式一：通过 Admin 界面

1. 访问 `http://localhost:8000/admin/django_q/schedule/`
2. 点击"添加 Schedule"
3. 填写任务信息：
   - **名称**: 任务名称
   - **函数**: 要执行的函数路径
   - **参数**: JSON 格式的参数
   - **调度类型**: 选择调度类型
   - **下次运行**: 设置首次执行时间

#### 方式二：通过代码创建

```python
from django_q.models import Schedule
from django.utils import timezone

# 创建每日执行的任务
schedule = Schedule.objects.create(
    name='每日测试任务',
    func='apps.scheduler.task_executor.execute_task',
    args='[1]',  # 任务ID
    schedule_type=Schedule.DAILY,
    next_run=timezone.now(),
    repeats=-1  # 无限次
)
```

### 暂停和恢复任务

#### 实现原理

**Django-Q 原生不支持暂停/恢复功能**，我们通过控制 `next_run` 字段来实现：

- **暂停任务**: 将 `next_run` 设置为 `None`
- **恢复任务**: 将 `next_run` 设置为当前时间

#### 代码实现

```python
from apps.scheduler.models import ScheduleConfig

# 暂停任务
config = ScheduleConfig.objects.get(schedule__id=schedule_id)
config.pause()

# 恢复任务
config.resume()
```

#### 暂停/恢复方法详解

**暂停任务**：
```python
def pause(self):
    """暂停任务"""
    self.status = 'PAUSED'
    self.save()
    # 暂停时将next_run设置为None，防止Django-Q调度器执行
    self.schedule.next_run = None
    self.schedule.save()
```

**恢复任务**：
```python
def resume(self):
    """恢复任务"""
    self.status = 'ACTIVE'
    self.save()
    # 恢复时重新计算next_run
    from django.utils import timezone
    self.schedule.next_run = timezone.now()
    self.schedule.save()
```

### 立即执行任务

```python
from apps.scheduler.models import ScheduleConfig

# 立即执行任务
config = ScheduleConfig.objects.get(schedule__id=schedule_id)
config.execute_now()
```

### 删除任务

```python
from django_q.models import Schedule

# 删除任务
schedule = Schedule.objects.get(id=schedule_id)
schedule.delete()
```

## 任务统计

### 统计字段说明

在 Admin 界面中，我们为 Schedule 添加了以下统计字段：

| 字段 | 说明 |
|------|------|
| 上次运行 | 显示任务最后一次执行的时间 |
| 成功/失败 | 显示任务执行的成功和失败次数 |

### 统计计算方式

#### 分组方式

任务统计按**所属模块**进行分组：

```python
# 获取所属模块作为group
group_name = schedule.name
try:
    config = ScheduleConfig.objects.get(schedule__id=schedule_id)
    group_name = config.get_module_display()
except Exception:
    pass
```

#### 统计查询

```python
from django_q.models import Success, Failure

# 统计成功次数
success_count = Success.objects.filter(group=group_name).count()

# 统计失败次数
failure_count = Failure.objects.filter(group=group_name).count()
```

### 兼容性处理

为了兼容历史数据，统计查询支持多种 group 值：

1. **所属模块**（优先）：`config.get_module_display()`
2. **任务名称**：`schedule.name`
3. **任务ID**：`str(schedule.id)`

```python
# 兼容多种group值
success_count = (
    Success.objects.filter(group=group_name).count() +
    Success.objects.filter(group=obj.name).count() +
    Success.objects.filter(group=str(obj.id)).count()
)
```

## Admin 界面定制

### 自定义 ScheduleAdmin

我们自定义了 `ScheduleAdmin` 来增强功能：

```python
from django.contrib import admin
from django_q.admin import ScheduleAdmin as DjangoQScheduleAdmin

class ScheduleAdmin(DjangoQScheduleAdmin):
    list_display = (
        'name', 'schedule_type', 'col_last_run', 'col_success_count',
        'next_run', 'repeats'
    )
    list_filter = ('schedule_type',)
    
    def col_last_run(self, obj):
        # 显示上次运行时间
        pass
    
    def col_success_count(self, obj):
        # 显示成功/失败次数
        pass
```

### 自定义过滤器

使用 Django-Q 原生的翻译字符串：

```python
class ScheduleTypeFilter(admin.SimpleListFilter):
    title = '调度类型'
    parameter_name = 'schedule_type'
    
    def lookups(self, request, model_admin):
        return [
            ('O', _('Once')),
            ('I', _('Minutes')),
            ('H', _('Hourly')),
            ('D', _('Daily')),
            ('W', _('Weekly')),
            ('BW', _('Biweekly')),
            ('M', _('Monthly')),
            ('BM', _('Bimonthly')),
            ('Q', _('Quarterly')),
            ('Y', _('Yearly')),
            ('C', _('Cron')),
        ]
```

### 翻译支持

所有调度类型都支持中文翻译：

| 英文 | 中文 |
|------|------|
| Once | 单次 |
| Minutes | 分钟 |
| Hourly | 每小时 |
| Daily | 每天 |
| Weekly | 每周 |
| Biweekly | 双周 |
| Monthly | 每月 |
| Bimonthly | 双月 |
| Quarterly | 每季度 |
| Yearly | 每年 |
| Cron | Cron表达式 |

## 任务执行

### 异步任务执行

使用 `async_task` 函数创建异步任务：

```python
from django_q import async_task

# 创建异步任务
task_id = async_task(
    'apps.scheduler.task_executor.execute_task',
    schedule_id,
    group=group_name  # 使用所属模块作为group
)
```

### 任务执行流程

1. **调度器检查**: Django-Q 调度器定期检查 Schedule 表
2. **创建任务**: 满足条件的任务被创建为异步任务
3. **执行任务**: Worker 执行任务逻辑
4. **记录结果**: 任务结果存储在 Task 表中
5. **更新统计**: Success/Failure 表记录执行结果

### 任务状态

任务执行有以下几种状态：

- **PENDING**: 等待执行
- **STARTED**: 开始执行
- **SUCCESS**: 执行成功
- **FAILURE**: 执行失败
- **STOPPED**: 被停止

## 常见问题

### 1. 任务没有按预期执行

**可能原因**：
- `next_run` 时间未到
- 任务被暂停（`next_run` 为 `None`）
- `repeats` 为 0（已完成）
- Django-Q Cluster 未运行

**解决方法**：
```python
# 检查任务状态
schedule = Schedule.objects.get(id=schedule_id)
print(f"Next run: {schedule.next_run}")
print(f"Repeats: {schedule.repeats}")

# 检查 Cluster 是否运行
# 查看 logs/qcluster.log
```

### 2. 暂停的任务还在执行

**可能原因**：
- 暂停时没有正确设置 `next_run` 为 `None`
- 任务已经在执行队列中

**解决方法**：
```python
# 手动设置 next_run 为 None
schedule = Schedule.objects.get(id=schedule_id)
schedule.next_run = None
schedule.save()
```

### 3. 统计数据不准确

**可能原因**：
- `group` 字段值不一致
- 历史数据使用旧的分组方式

**解决方法**：
- 统计查询支持多种 group 值（模块、名称、ID）
- 确保新任务使用正确的 group 值

### 4. 如何查看任务执行日志

**方法一**：查看日志文件
```bash
# 查看调度器日志
tail -f logs/scheduler.log

# 查看 Cluster 日志
tail -f logs/qcluster.log
```

**方法二**：在 Admin 界面查看
- 访问 `http://localhost:8000/admin/django_q/task/`
- 查看任务执行详情

## 最佳实践

### 1. 任务命名规范

使用清晰的任务名称，包含模块和功能信息：

```python
# 好的命名
name = '[API测试] 每日回归测试'
name = '[UI自动化] 每周冒烟测试'

# 不好的命名
name = 'test1'
name = '任务'
```

### 2. 参数管理

将复杂参数存储在配置表中，而不是直接写在 Schedule 中：

```python
# 好的做法
args = '[]'  # 空参数
kwargs = '{}'  # 空参数
# 在执行函数中从配置表读取参数

# 不好的做法
args = '[1, 2, 3, 4, 5, ...]'  # 太长的参数列表
kwargs = '{"param1": "value1", "param2": "value2", ...}'  # 太多的参数
```

### 3. 错误处理

在任务执行函数中添加完善的错误处理：

```python
def execute_task(schedule_id):
    try:
        # 任务逻辑
        pass
    except Exception as e:
        logger.error(f"任务执行失败: {e}")
        raise
```

### 4. 日志记录

在关键步骤添加日志记录：

```python
logger.info(f"开始执行任务: {schedule.name}")
logger.info(f"任务参数: {args}, {kwargs}")
logger.info(f"任务执行完成: {result}")
```

### 5. 监控和告警

配置任务失败告警：

```python
# 在 ScheduleConfig 中配置通知
config.notify_on_failure = True
config.notify_emails = ['admin@example.com']
config.save()
```

## 相关文档

- [Django-Q 官方文档](https://django-q2.readthedocs.io/)
- [项目 README](../../README.md)


