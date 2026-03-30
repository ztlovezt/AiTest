import logging
import threading
import os
from asgiref.sync import sync_to_async
from django.db import connection, DatabaseError
from django.utils import timezone
from django.db import models
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from .models import AiProject, AICase, AIExecutionRecord
from .serializers import AiProjectSerializer, AICaseSerializer, AIExecutionRecordSerializer
from .ai_agent import run_full_process_sync

logger = logging.getLogger(__name__)

# 全局字典，用于存储停止信号
STOP_SIGNALS = {}

class AiProjectViewSet(viewsets.ModelViewSet):
    queryset = AiProject.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = AiProjectSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        return AiProject.objects.filter(
            models.Q(unified_meta_project__owner=user) | 
            models.Q(unified_meta_project__members__user=user) |
            models.Q(unified_meta_project__isnull=True)
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class AICaseViewSet(viewsets.ModelViewSet):
    queryset = AICase.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = AICaseSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project']
    search_fields = ['name', 'description', 'task_description']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        accessible_projects = AiProject.objects.filter(
            models.Q(unified_meta_project__owner=user) | 
            models.Q(unified_meta_project__members__user=user) |
            models.Q(unified_meta_project__isnull=True)  # 允许访问没有关联元项目的 AiProject（例如默认迁移项目）
        ).distinct()
        return AICase.objects.filter(
            models.Q(project__in=accessible_projects) | models.Q(project__isnull=True)
        ).distinct()

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        instance = serializer.save()

    def perform_destroy(self, instance):
        if instance.unified_meta_project:
            meta_project = instance.unified_meta_project
            # 找到并删除对应的关联记录
            from apps.unified_projects.models import ProjectModule
            ProjectModule.objects.filter(meta_project=meta_project, module_type='AI_TEST').delete()
            
            instance.unified_meta_project = None
            instance.save()
            # 检查是否还有其他模块关联，如果没有才删除 meta_project
            if meta_project.modules.count() == 0:
                meta_project.delete()
        instance.delete()

    @action(detail=True, methods=['post'])
    def run(self, request, pk=None):
        """执行 AI 用例"""
        ai_case = self.get_object()

        # 创建执行记录
        execution_record = AIExecutionRecord.objects.create(
            project=ai_case.project,
            ai_case=ai_case,
            case_name=ai_case.name,
            task_description=ai_case.task_description,
            status='running',
            executed_by=request.user,
            logs="正在分析任务...\n"
        )

        # 异步执行
        import threading
        import os
        from asgiref.sync import sync_to_async
        from django.db import connection, DatabaseError
        from .ai_agent import run_full_process_sync

        def run_task():
            # 注册停止信号
            STOP_SIGNALS[execution_record.id] = False

            # 关键修复：关闭旧连接，避免子线程共享主线程的连接
            try:
                connection.close()
            except:
                pass

            # 设置环境变量，允许在后台线程中使用同步 ORM
            os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'

            def safe_save(record, update_fields=None, max_retries=3):
                """安全的保存方法，带有重试机制"""
                for attempt in range(max_retries):
                    try:
                        record.save(update_fields=update_fields)
                        return True
                    except (DatabaseError, Exception) as e:
                        error_str = str(e)
                        # 检查是否是MySQL连接错误
                        if '2006' in error_str or 'MySQL server has gone away' in error_str or '0' == error_str:
                            if attempt < max_retries - 1:
                                logger.warning(f"数据库连接失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                                # 关闭旧连接并重试
                                try:
                                    connection.close()
                                except:
                                    pass
                                import time
                                time.sleep(0.5)  # 等待一下再重试
                                continue
                            else:
                                logger.error(f"数据库保存失败，已达最大重试次数: {e}")
                                raise
                        else:
                            # 其他错误直接抛出
                            logger.error(f"数据库保存失败: {e}")
                            raise
                return False

            try:
                def should_stop():
                    return STOP_SIGNALS.get(execution_record.id, False)

                async def on_analysis_complete(planned_tasks):
                    execution_record.planned_tasks = sanitize_planned_tasks(planned_tasks)
                    execution_record.logs += "任务分析完成，开始执行...\n"
                    await sync_to_async(safe_save)(execution_record, update_fields=['planned_tasks', 'logs'])

                async def on_step_update(step_info):
                    try:
                        # 处理日志
                        if step_info.get('type') == 'log':
                            content = step_info.get('content')
                            if content:
                                execution_record.logs += content
                                await sync_to_async(safe_save)(execution_record, update_fields=['logs'])
                            return

                        # 处理任务状态
                        task_id = step_info.get('task_id')
                        status = step_info.get('status')
                        if task_id and status:
                            execution_record.planned_tasks = sanitize_planned_tasks(execution_record.planned_tasks)
                            if str(status).strip().lower() == 'completed':
                                backfilled_ids = backfill_prior_pending_tasks(
                                    execution_record.planned_tasks,
                                    task_id
                                )
                                if backfilled_ids:
                                    execution_record.logs += (
                                        f"\n[System] 已补齐遗漏标记的前序子任务: "
                                        f"{', '.join(map(str, backfilled_ids))}"
                                    )
                            updated = update_planned_task_status(
                                execution_record.planned_tasks,
                                task_id,
                                status
                            )
                            if updated:
                                update_fields = ['planned_tasks']
                                if str(status).strip().lower() == 'completed' and 'backfilled_ids' in locals() and backfilled_ids:
                                    update_fields.append('logs')
                                await sync_to_async(safe_save)(execution_record, update_fields=update_fields)
                    except Exception as e:
                        logger.error(f"更新步骤状态失败: {e}")

                history = run_full_process_sync(
                    ai_case.task_description,
                    analysis_callback=on_analysis_complete,
                    step_callback=on_step_update,
                    should_stop=should_stop
                )

                # 检查是否是手动停止
                if should_stop():
                    execution_record.status = 'stopped'
                    execution_record.logs += "\n[System] 任务已由用户停止。"
                else:
                    execution_record.planned_tasks = sanitize_planned_tasks(execution_record.planned_tasks)
                    done_backfilled_ids = backfill_pending_tasks_if_done_success(
                        execution_record.planned_tasks,
                        history,
                        execution_record.logs
                    )
                    if done_backfilled_ids:
                        execution_record.logs += (
                            f"\n[System] 检测到 done(success=true)，自动补齐完成子任务: "
                            f"{', '.join(map(str, done_backfilled_ids))}。"
                        )
                    execution_record.status, task_summary = resolve_execution_status(execution_record.planned_tasks)
                    if execution_record.status == 'passed':
                        execution_record.logs += "\n执行完成。"
                    else:
                        execution_record.logs += "\n执行结束，但存在未完成或失败的子任务。"
                    logger.info(
                        "🏁 Task completion summary: "
                        f"{task_summary['completed']}/{task_summary['total']} completed, "
                        f"{task_summary['failed']} failed, "
                        f"{task_summary['pending'] + task_summary['in_progress']} pending"
                    )

                execution_record.end_time = timezone.now()
                execution_record.duration = (execution_record.end_time - execution_record.start_time).total_seconds()

                # 格式化 history 为日志 (如果不是停止状态)
                steps = []
                if history:
                    if hasattr(history, 'steps'):
                        steps = [extract_step_info(s, i) for i, s in enumerate(history.steps)]

                execution_record.steps_completed = steps

                # 自动标记已完成的任务
                if execution_record.planned_tasks:
                    execution_record.planned_tasks = sanitize_planned_tasks(execution_record.planned_tasks)
                    self._auto_mark_completed_tasks(execution_record)
                    execution_record.logs = append_execution_summary(
                        execution_record.logs,
                        summarize_planned_tasks(execution_record.planned_tasks)
                    )

                # 处理GIF录制文件
                self._process_gif_recording(execution_record, history)

                safe_save(execution_record)

            except Exception as e:
                error_message = str(e)
                logger.error(f"AI 执行线程异常: {error_message}", exc_info=True)
                execution_record.planned_tasks = sanitize_planned_tasks(execution_record.planned_tasks)
                current_summary = summarize_planned_tasks(execution_record.planned_tasks)
                all_tasks_terminal_and_success = (
                    current_summary['total'] > 0
                    and current_summary['failed'] == 0
                    and (current_summary['pending'] + current_summary['in_progress']) == 0
                )

                failed_task_id = None
                if all_tasks_terminal_and_success:
                    execution_record.status = 'passed'
                    execution_record.logs += (
                        f"\n[System] 捕获到执行期异常，但子任务已全部完成，按通过处理。"
                        f"异常信息: {error_message}"
                    )
                else:
                    failed_task_id = None if is_infrastructure_failure(error_message) else mark_first_active_task(execution_record.planned_tasks, 'failed')
                    execution_record.status = 'failed'
                    if 'Execution LLM unavailable' in error_message:
                        execution_record.logs += f"\n执行出错: AI 执行模型连接失败。{error_message}"
                    else:
                        execution_record.logs += f"\n执行出错: {error_message}"
                    if failed_task_id is not None:
                        execution_record.logs += f"\n[System] 子任务 {failed_task_id} 已自动标记为失败。"

                execution_record.end_time = timezone.now()
                execution_record.duration = (execution_record.end_time - execution_record.start_time).total_seconds()
                execution_record.logs = append_execution_summary(
                    execution_record.logs,
                    summarize_planned_tasks(execution_record.planned_tasks)
                )
                try:
                    safe_save(execution_record)
                except:
                    # 如果保存失败，至少尝试保存基本信息
                    logger.error(f"保存失败状态时出错: {e}")
                    pass
            finally:
                # 清理停止信号
                if execution_record.id in STOP_SIGNALS:
                    del STOP_SIGNALS[execution_record.id]

        thread = threading.Thread(target=run_task)
        thread.daemon = True
        thread.start()

        return Response({
            'message': 'AI 用例开始执行',
            'execution_id': execution_record.id
        })

    def _process_gif_recording(self, execution_record, history):
        """
        处理GIF录制文件
        在执行完成后查找生成的GIF文件并保存路径到数据库
        """
        try:
            import os
            from django.conf import settings
            from datetime import datetime

            # browser-use 默认生成的GIF文件名（固定为agent_history.gif）
            default_gif_path = os.path.join(os.getcwd(), 'agent_history.gif')

            # 如果找到GIF文件，移动到media/ai_recording目录并重命名
            if os.path.exists(default_gif_path):
                import shutil

                # 创建录制文件目录 - 使用配置文件中的路径
                gif_dir = os.path.join(settings.MEDIA_ROOT, settings.ALLURE_AI_RECORDING)
                os.makedirs(gif_dir, exist_ok=True)

                # 生成新的文件名：用例名称+年月日时分秒
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                # 清理用例名称中的非法字符
                safe_case_name = "".join(
                    [c if c.isalnum() or c in (' ', '_', '-') else '_' for c in execution_record.case_name])
                new_gif_filename = f"{safe_case_name}_{timestamp}.gif"
                new_gif_path = os.path.join(gif_dir, new_gif_filename)

                # 移动并重命名文件
                shutil.move(default_gif_path, new_gif_path)

                # 保存相对路径到数据库（使用正斜杠，确保跨平台兼容）- 使用配置文件中的路径
                # 注意：不要包含 'media/' 前缀，因为 MEDIA_URL 已经是 '/media/'
                relative_path = f'{settings.ALLURE_AI_RECORDING}/{new_gif_filename}'
                execution_record.gif_path = relative_path

                logger.info(f"✅ GIF recording saved to: {relative_path}")
            else:
                logger.warning(f"⚠️ GIF file not found at: {default_gif_path}")
        except Exception as e:
            logger.error(f"❌ Error moving GIF file: {e}")
            logger.warning(f"⚠️ Failed to process GIF recording: {e}")

    def _auto_mark_completed_tasks(self, execution_record):
        """
        自动标记已完成的任务
        通过分析执行历史和当前任务状态，自动标记那些已经执行但未被标记完成的任务

        注意：已移除统一标记逻辑，任务状态完全由AI智能体通过mark_task_complete控制
        - 执行成功时标记为completed
        - 执行失败时标记为failed
        - 跳过执行时标记为skipped
        - 未执行时标记为pending
        """
        try:
            # 记录初始状态
            initial_completed = 0
            initial_pending = 0
            initial_failed = 0
            initial_skipped = 0

            if execution_record.planned_tasks:
                execution_record.planned_tasks = sanitize_planned_tasks(execution_record.planned_tasks)
                initial_completed = len([t for t in execution_record.planned_tasks if t.get('status') == 'completed'])
                initial_pending = len([t for t in execution_record.planned_tasks if t.get('status') == 'pending'])
                initial_failed = len([t for t in execution_record.planned_tasks if t.get('status') == 'failed'])
                initial_skipped = len([t for t in execution_record.planned_tasks if t.get('status') == 'skipped'])
                
                logger.info(f"📊 Task status summary: {initial_completed} completed, {initial_pending} pending, {initial_failed} failed, {initial_skipped} skipped")

            # 不再自动标记所有任务为完成
            # 任务状态完全由AI智能体通过mark_task_complete来控制
            logger.info("📋 Task statuses are controlled by AI agent via mark_task_complete action")

        except Exception as e:
            logger.warning(f"⚠️ Failed to auto-mark completed tasks: {e}")


# 全局停止信号字典 {execution_id: bool}
STOP_SIGNALS = {}

TERMINAL_TASK_STATUSES = {'completed', 'failed', 'skipped'}
ACTIVE_TASK_STATUSES = {'pending', 'in_progress'}


def sanitize_planned_tasks(planned_tasks):
    """清洗并标准化 planned_tasks，确保元素为 dict。"""
    if not planned_tasks:
        return []

    if not isinstance(planned_tasks, list):
        planned_tasks = [planned_tasks]

    flattened = []
    for item in planned_tasks:
        if isinstance(item, list):
            flattened.extend(item)
        else:
            flattened.append(item)

    normalized = []
    for task in flattened:
        if isinstance(task, dict):
            normalized.append(task)
            continue
        if hasattr(task, 'model_dump'):
            try:
                dumped = task.model_dump()
                if isinstance(dumped, dict):
                    normalized.append(dumped)
                continue
            except Exception:
                continue
        if hasattr(task, '__dict__'):
            task_dict = dict(task.__dict__)
            if isinstance(task_dict, dict):
                normalized.append(task_dict)
    return normalized


def update_planned_task_status(planned_tasks, task_id, task_status):
    """更新子任务状态，返回是否命中任务。"""
    if not planned_tasks or task_id is None or not task_status:
        return False

    normalized_tasks = sanitize_planned_tasks(planned_tasks)
    if isinstance(planned_tasks, list):
        planned_tasks[:] = normalized_tasks

    normalized_status = str(task_status).strip().lower()
    for task in normalized_tasks:
        if str(task.get('id')) == str(task_id):
            task['status'] = normalized_status
            return True
    return False


def backfill_prior_pending_tasks(planned_tasks, current_task_id):
    """受限补齐：仅在强依赖场景下补齐紧邻前一步遗漏标记。"""
    if not planned_tasks or current_task_id is None:
        return []

    normalized_tasks = sanitize_planned_tasks(planned_tasks)
    if isinstance(planned_tasks, list):
        planned_tasks[:] = normalized_tasks

    try:
        current_task_id_int = int(current_task_id)
    except (TypeError, ValueError):
        return []

    task_by_id = {}
    for task in normalized_tasks:
        try:
            task_by_id[int(task.get('id'))] = task
        except (TypeError, ValueError):
            continue

    current_task = task_by_id.get(current_task_id_int)
    previous_task = task_by_id.get(current_task_id_int - 1)
    if not current_task or not previous_task:
        return []

    if previous_task.get('status', 'pending') not in ACTIVE_TASK_STATUSES:
        return []

    previous_desc = str(previous_task.get('description', '')).strip()
    current_desc = str(current_task.get('description', '')).strip()

    # 验证/检查类任务必须显式标记，禁止自动补齐
    verification_keywords = ['校验', '确认', '检查', '验证', '断言']
    if any(keyword in previous_desc for keyword in verification_keywords):
        return []

    dependency_pairs = [
        (['访问', '打开', '进入'], ['搜索', '输入', '点击', '查看']),
        (['搜索'], ['点击第', '点击第2条', '点击第二条', '查看详情']),
        (['点击第', '点击第2条', '点击第二条', '查看详情'], ['关闭', '关闭该标签页', '关闭标签页']),
        (['打开详情', '查看详情'], ['关闭', '返回']),
    ]

    def matches_any(text, keywords):
        return any(keyword in text for keyword in keywords)

    allowed = any(
        matches_any(previous_desc, prev_keywords) and matches_any(current_desc, curr_keywords)
        for prev_keywords, curr_keywords in dependency_pairs
    )

    if not allowed:
        return []

    previous_task['status'] = 'completed'
    return [current_task_id_int - 1]


def mark_first_active_task(planned_tasks, task_status):
    """在执行异常时为第一个未终态任务补一个状态。"""
    if not planned_tasks:
        return None

    normalized_tasks = sanitize_planned_tasks(planned_tasks)
    if isinstance(planned_tasks, list):
        planned_tasks[:] = normalized_tasks

    normalized_status = str(task_status).strip().lower()
    for task in normalized_tasks:
        if task.get('status', 'pending') in ACTIVE_TASK_STATUSES:
            task['status'] = normalized_status
            return task.get('id')
    return None


def summarize_planned_tasks(planned_tasks):
    """汇总子任务状态。"""
    summary = {
        'total': 0,
        'completed': 0,
        'failed': 0,
        'skipped': 0,
        'pending': 0,
        'in_progress': 0,
    }
    if not planned_tasks:
        return summary

    normalized_tasks = sanitize_planned_tasks(planned_tasks)
    if isinstance(planned_tasks, list):
        planned_tasks[:] = normalized_tasks

    summary['total'] = len(normalized_tasks)
    for task in normalized_tasks:
        task_status = task.get('status', 'pending')
        if task_status in summary:
            summary[task_status] += 1
        else:
            summary['pending'] += 1
    return summary


def resolve_execution_status(planned_tasks):
    """根据子任务实际状态推导整单状态。"""
    summary = summarize_planned_tasks(planned_tasks)

    if summary['total'] == 0:
        return 'passed', summary
    if summary['failed'] > 0:
        return 'failed', summary
    if summary['pending'] > 0 or summary['in_progress'] > 0:
        return 'failed', summary
    return 'passed', summary


def append_execution_summary(logs, summary):
    """把任务统计附加到日志中。"""
    if summary['total'] == 0:
        return logs
    return (
        f"{logs}\n[System] 子任务统计: 总数 {summary['total']}，"
        f"已完成 {summary['completed']}，失败 {summary['failed']}，"
        f"跳过 {summary['skipped']}，待处理 {summary['pending'] + summary['in_progress']}。"
    )


def backfill_pending_tasks_if_done_success(planned_tasks, history, logs_text=None):
    """若历史中已出现 done(success=True)，则将剩余 pending/in_progress 任务补标为 completed。"""
    normalized_tasks = sanitize_planned_tasks(planned_tasks)
    if isinstance(planned_tasks, list):
        planned_tasks[:] = normalized_tasks

    if not normalized_tasks:
        return []

    def _normalize_action_dict(action):
        action_dict = None
        if isinstance(action, dict):
            action_dict = action
        elif hasattr(action, 'model_dump'):
            try:
                action_dict = action.model_dump()
            except Exception:
                action_dict = None
        elif hasattr(action, '_action_dict'):
            action_dict = getattr(action, '_action_dict', None)

        if isinstance(action_dict, list):
            for item in action_dict:
                if isinstance(item, dict):
                    return item
            return {}
        return action_dict if isinstance(action_dict, dict) else {}

    def _is_done_success(done_params):
        if isinstance(done_params, dict):
            success_value = done_params.get('success')
            if isinstance(success_value, bool):
                return success_value
            if isinstance(success_value, str):
                return success_value.strip().lower() == 'true'
            return False
        if isinstance(done_params, list):
            return any(_is_done_success(item) for item in done_params)
        if hasattr(done_params, 'success'):
            success_value = getattr(done_params, 'success', False)
            if isinstance(success_value, bool):
                return success_value
            if isinstance(success_value, str):
                return success_value.strip().lower() == 'true'
        return False

    has_done_success = False
    if history and hasattr(history, 'steps'):
        for step in getattr(history, 'steps', []):
            actions = getattr(step, 'actions', [])
            for action in actions:
                action_dict = _normalize_action_dict(action)
                if not action_dict:
                    continue

                done_params = action_dict.get('done')
                if _is_done_success(done_params):
                    has_done_success = True
                    break
            if has_done_success:
                break

    if not has_done_success and logs_text:
        logs_lower = str(logs_text).lower()
        has_done_success = (
            "done: success: true" in logs_lower
            or "所有9个任务已成功完成" in str(logs_text)
            or "successfully completed all 9 tasks" in logs_lower
        )

    if not has_done_success:
        return []

    backfilled = []
    for task in normalized_tasks:
        status = str(task.get('status', 'pending')).lower()
        if status in ACTIVE_TASK_STATUSES:
            task['status'] = 'completed'
            if task.get('id') is not None:
                backfilled.append(task.get('id'))
    return backfilled

def is_infrastructure_failure(error_message: str) -> bool:
    """判断是否为模型/网络/初始化类故障，这类问题不应直接把首个子任务标失败。"""
    message = (error_message or '').lower()
    infra_markers = [
        'execution llm unavailable',
        'connection error',
        'timed out',
        'timeout',
        'api key',
        'authentication',
        'unauthorized',
        'forbidden',
        'rate limit',
        'service unavailable',
    ]
    return any(marker in message for marker in infra_markers)


class AIExecutionRecordViewSet(viewsets.ModelViewSet):
    """AI执行记录视图集"""
    queryset = AIExecutionRecord.objects.all()
    serializer_class = AIExecutionRecordSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['project', 'ai_case', 'status']
    ordering = ['-start_time']

    def get_queryset(self):
        user = self.request.user
        accessible_projects = AiProject.objects.filter(
            models.Q(unified_meta_project__owner=user) | 
            models.Q(unified_meta_project__members__user=user) |
            models.Q(unified_meta_project__isnull=True)  # 允许访问没有关联元项目的 AiProject（例如默认迁移项目）
        ).distinct()
        return AIExecutionRecord.objects.filter(
            models.Q(project__in=accessible_projects) | models.Q(project__isnull=True)
        ).distinct()

    def perform_destroy(self, instance):
        instance.delete()

    @action(detail=False, methods=['post'])
    def batch_delete(self, request):
        """批量删除AI执行记录"""
        try:
            ids = request.data.get('ids', [])

            # 验证ids参数
            if not ids:
                return Response({'error': '请选择要删除的记录'}, status=status.HTTP_400_BAD_REQUEST)

            # 确保ids是列表
            if not isinstance(ids, list):
                return Response({'error': 'ids参数格式错误，应为数组'}, status=status.HTTP_400_BAD_REQUEST)

            # 只能删除自己有权限的项目下的记录
            queryset = self.get_queryset()
            records_to_delete = queryset.filter(id__in=ids)

            # 检查是否有权限删除这些记录
            if not records_to_delete.exists():
                return Response({'error': '未找到可删除的记录或没有权限删除'}, status=status.HTTP_404_NOT_FOUND)

            # 获取可删除记录的ID列表，避免对distinct()后的queryset调用delete()
            deletable_ids = list(records_to_delete.values_list('id', flat=True))

            # 使用ID列表直接删除，避免distinct()的问题
            deleted_count = AIExecutionRecord.objects.filter(id__in=deletable_ids).delete()[0]

            return Response({'message': f'成功删除 {deleted_count} 条记录', 'deleted_count': deleted_count})
        except Exception as e:
            logger.error(f"批量删除AI执行记录失败: {str(e)}", exc_info=True)
            return Response({'error': f'批量删除失败: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='run_adhoc')
    def run_adhoc(self, request):
        """执行临时 AI 任务"""
        project_id = request.data.get('project_id')
        task_description = request.data.get('task_description')
        execution_mode = request.data.get('execution_mode', 'text')  # 默认文本模式
        enable_gif = request.data.get('enable_gif', True)  # GIF录制开关，默认开启

        if not task_description:
            return Response({'error': '缺少任务描述参数'}, status=status.HTTP_400_BAD_REQUEST)

        # 获取项目对象（如果提供了project_id）
        project = None
        if project_id:
            try:
                project = AiProject.objects.get(id=project_id)
            except AiProject.DoesNotExist:
                return Response({'error': '项目不存在'}, status=status.HTTP_404_NOT_FOUND)

        # 创建执行记录
        execution_record = AIExecutionRecord.objects.create(
            project=project,
            case_name="Adhoc Task",
            task_description=task_description,
            execution_mode=execution_mode,
            status='running',
            executed_by=request.user,
            logs="正在分析任务...\n"
        )

        # 异步执行
        import threading
        import os
        from asgiref.sync import sync_to_async
        from django.db import connection, DatabaseError
        from .ai_agent import run_full_process_sync

        def run_task():
            # 注册停止信号
            STOP_SIGNALS[execution_record.id] = False

            # 关键修复：关闭旧连接，避免子线程共享主线程的连接
            try:
                connection.close()
            except:
                pass

            # 设置环境变量，允许在后台线程中使用同步 ORM
            os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'

            def safe_save(record, update_fields=None, max_retries=3):
                """安全的保存方法，带有重试机制"""
                for attempt in range(max_retries):
                    try:
                        record.save(update_fields=update_fields)
                        return True
                    except (DatabaseError, Exception) as e:
                        error_str = str(e)
                        # 检查是否是MySQL连接错误
                        if '2006' in error_str or 'MySQL server has gone away' in error_str or '0' == error_str:
                            if attempt < max_retries - 1:
                                logger.warning(f"数据库连接失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                                # 关闭旧连接并重试
                                try:
                                    connection.close()
                                except:
                                    pass
                                import time
                                time.sleep(0.5)  # 等待一下再重试
                                continue
                            else:
                                logger.error(f"数据库保存失败，已达最大重试次数: {e}")
                                raise
                        else:
                            # 其他错误直接抛出
                            logger.error(f"数据库保存失败: {e}")
                            raise
                return False

            try:
                # 定义异步安全的 should_stop
                async def should_stop_async():
                    # 优先检查内存信号
                    if STOP_SIGNALS.get(execution_record.id, False):
                        return True
                    # 兜底检查数据库状态 (使用 sync_to_async 避免异步上下文错误)
                    # 关键修复：只刷新 status 字段，避免覆盖内存中最新的 planned_tasks
                    await sync_to_async(execution_record.refresh_from_db)(fields=['status'])
                    return execution_record.status == 'stopped'

                # 定义同步版本的 should_stop 用于最后检查
                def should_stop_sync():
                    if STOP_SIGNALS.get(execution_record.id, False):
                        return True
                    # 只刷新 status 字段，避免覆盖内存中最新的 planned_tasks
                    # 因为 planned_tasks 已经由 on_step_update 实时更新并在内存中是最新的
                    execution_record.refresh_from_db(fields=['status'])
                    return execution_record.status == 'stopped'

                async def on_analysis_complete(planned_tasks):
                    execution_record.planned_tasks = sanitize_planned_tasks(planned_tasks)
                    execution_record.logs += "任务分析完成，开始执行...\n"
                    await sync_to_async(safe_save)(execution_record, update_fields=['planned_tasks', 'logs'])

                async def on_step_update(step_info):
                    try:
                        # 处理日志
                        if step_info.get('type') == 'log':
                            content = step_info.get('content')
                            if content:
                                execution_record.logs += content
                                # 立即保存到数据库，确保前端轮询能看到最新日志
                                await sync_to_async(safe_save)(execution_record, update_fields=['logs'])
                            return

                        # 处理任务状态
                        task_id = step_info.get('task_id')
                        status = step_info.get('status')
                        logger.info(f"DEBUG: on_step_update received: task_id={task_id}, status={status}")

                        if task_id and status:
                            updated = False
                            if execution_record.planned_tasks:
                                execution_record.planned_tasks = sanitize_planned_tasks(execution_record.planned_tasks)
                                old_status = None
                                for task in execution_record.planned_tasks:
                                    if str(task.get('id')) == str(task_id):
                                        old_status = task.get('status', 'pending')
                                        break
                                backfilled_ids = []
                                if str(status).strip().lower() == 'completed':
                                    backfilled_ids = backfill_prior_pending_tasks(
                                        execution_record.planned_tasks,
                                        task_id
                                    )
                                    if backfilled_ids:
                                        execution_record.logs += (
                                            f"\n[System] 已补齐遗漏标记的前序子任务: "
                                            f"{', '.join(map(str, backfilled_ids))}"
                                        )
                                updated = update_planned_task_status(
                                    execution_record.planned_tasks,
                                    task_id,
                                    status
                                )
                                if updated:
                                    logger.info(f"DEBUG: Updated task {task_id} from {old_status} to {status}")
                            if updated:
                                # 立即保存到数据库，确保前端轮询能看到最新状态
                                update_fields = ['planned_tasks']
                                if 'backfilled_ids' in locals() and backfilled_ids:
                                    update_fields.append('logs')
                                await sync_to_async(safe_save)(execution_record, update_fields=update_fields)
                            else:
                                logger.warning(
                                    f"DEBUG: Task ID {task_id} not found in planned_tasks: {execution_record.planned_tasks}")
                    except Exception as e:
                        logger.error(f"更新步骤状态失败: {e}", exc_info=True)

                history = run_full_process_sync(
                    task_description,
                    analysis_callback=on_analysis_complete,
                    step_callback=on_step_update,
                    should_stop=should_stop_async,  # 传递异步版本
                    execution_mode=execution_mode,
                    enable_gif=enable_gif,  # 传递GIF录制开关
                    case_name=task_description[:50] if task_description else "Adhoc Task"  # 传递用例名称用于GIF文件命名
                )

                # 检查是否是手动停止 (使用同步版本)
                if should_stop_sync():
                    execution_record.status = 'stopped'
                    execution_record.logs += "\n[System] 任务已由用户停止。"
                else:
                    execution_record.planned_tasks = sanitize_planned_tasks(execution_record.planned_tasks)
                    done_backfilled_ids = backfill_pending_tasks_if_done_success(
                        execution_record.planned_tasks,
                        history,
                        execution_record.logs
                    )
                    if done_backfilled_ids:
                        execution_record.logs += (
                            f"\n[System] 检测到 done(success=true)，自动补齐完成子任务: "
                            f"{', '.join(map(str, done_backfilled_ids))}。"
                        )
                    # 关键修复：移除可能导致数据回滚的 refresh_from_db 调用
                    # 内存中的 execution_record.planned_tasks 已经由 on_step_update 实时更新并在内存中是最新的
                    # 信任内存中的状态，而不是去数据库拉取（可能存在异步写入延迟）
                    # execution_record.refresh_from_db(fields=['planned_tasks'])
                    
                    execution_record.status, task_summary = resolve_execution_status(execution_record.planned_tasks)
                    
                    # 添加详细调试日志，以便排查问题
                    logger.info(f"🔍 Final task status check before save: {task_summary}")
                    if execution_record.status != 'passed':
                        logger.warning(f"⚠️ Execution failed despite tasks completed? Tasks: {execution_record.planned_tasks}")

                    if execution_record.status == 'passed':
                        execution_record.logs += "\n执行完成。"
                    else:
                        execution_record.logs += "\n执行结束，但存在未完成或失败的子任务。"
                    logger.info(
                        "🏁 Task completion summary: "
                        f"{task_summary['completed']}/{task_summary['total']} completed, "
                        f"{task_summary['failed']} failed, "
                        f"{task_summary['pending'] + task_summary['in_progress']} pending"
                    )

                execution_record.end_time = timezone.now()
                execution_record.duration = (execution_record.end_time - execution_record.start_time).total_seconds()

                # 格式化 history 为日志 (如果不是停止状态)
                steps = []
                if history:
                    if hasattr(history, 'steps'):
                        steps = [extract_step_info(s, i) for i, s in enumerate(history.steps)]

                execution_record.steps_completed = steps

                # 自动标记已完成的任务
                if execution_record.planned_tasks:
                    execution_record.planned_tasks = sanitize_planned_tasks(execution_record.planned_tasks)
                    self._auto_mark_completed_tasks(execution_record)
                    execution_record.logs = append_execution_summary(
                        execution_record.logs,
                        summarize_planned_tasks(execution_record.planned_tasks)
                    )

                # 处理GIF录制文件
                self._process_gif_recording(execution_record, history)

                safe_save(execution_record)

            except Exception as e:
                error_message = str(e)
                logger.error(f"AI adhoc 执行线程异常: {error_message}", exc_info=True)
                execution_record.planned_tasks = sanitize_planned_tasks(execution_record.planned_tasks)
                current_summary = summarize_planned_tasks(execution_record.planned_tasks)
                all_tasks_terminal_and_success = (
                    current_summary['total'] > 0
                    and current_summary['failed'] == 0
                    and (current_summary['pending'] + current_summary['in_progress']) == 0
                )

                failed_task_id = None
                if all_tasks_terminal_and_success:
                    execution_record.status = 'passed'
                    execution_record.logs += (
                        f"\n[System] 捕获到执行期异常，但子任务已全部完成，按通过处理。"
                        f"异常信息: {error_message}"
                    )
                else:
                    failed_task_id = None if is_infrastructure_failure(error_message) else mark_first_active_task(execution_record.planned_tasks, 'failed')
                    execution_record.status = 'failed'
                    if 'Execution LLM unavailable' in error_message:
                        execution_record.logs += f"\n执行出错: AI 执行模型连接失败。{error_message}"
                    else:
                        execution_record.logs += f"\n执行出错: {error_message}"
                    if failed_task_id is not None:
                        execution_record.logs += f"\n[System] 子任务 {failed_task_id} 已自动标记为失败。"

                execution_record.end_time = timezone.now()
                execution_record.duration = (execution_record.end_time - execution_record.start_time).total_seconds()
                execution_record.logs = append_execution_summary(
                    execution_record.logs,
                    summarize_planned_tasks(execution_record.planned_tasks)
                )
                try:
                    safe_save(execution_record)
                except:
                    # 如果保存失败，至少尝试保存基本信息
                    logger.error(f"保存失败状态时出错: {e}")
                    pass
            finally:
                # 清理停止信号
                if execution_record.id in STOP_SIGNALS:
                    del STOP_SIGNALS[execution_record.id]

        thread = threading.Thread(target=run_task)
        thread.daemon = True
        thread.start()

        return Response({
            'message': 'AI 任务开始执行',
            'execution_id': execution_record.id
        })

    @action(detail=True, methods=['post'], url_path='stop')
    def stop_task(self, request, pk=None):
        """停止正在执行的任务"""
        try:
            execution_id = int(pk)
            if execution_id in STOP_SIGNALS:
                STOP_SIGNALS[execution_id] = True
                return Response({'message': '已发送停止信号'})
            else:
                # 如果不在内存中，可能已经结束，或者重启过服务
                # 尝试直接更新数据库状态
                record = self.get_object()
                if record.status == 'running':
                    record.status = 'stopped'
                    record.end_time = timezone.now()
                    record.logs += "\n[System] 任务被强制标记为停止（未在运行队列中找到）。"
                    record.save()
                    return Response({'message': '任务已标记为停止'})
                return Response({'message': '任务不在运行中'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _process_gif_recording(self, execution_record, history):
        """
        处理GIF录制文件
        在执行完成后查找生成的GIF文件并保存路径到数据库
        """
        try:
            import os
            from django.conf import settings
            from datetime import datetime

            # browser-use 默认生成的GIF文件名（固定为agent_history.gif）
            default_gif_path = os.path.join(os.getcwd(), 'agent_history.gif')

            # 如果找到GIF文件，移动到media/ai_recording目录并重命名
            if os.path.exists(default_gif_path):
                import shutil

                # 创建录制文件目录 - 使用配置文件中的路径
                gif_dir = os.path.join(settings.MEDIA_ROOT, settings.ALLURE_AI_RECORDING)
                os.makedirs(gif_dir, exist_ok=True)

                # 生成新的文件名：用例名称+年月日时分秒
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                # 清理用例名称中的非法字符
                safe_case_name = "".join(
                    [c if c.isalnum() or c in (' ', '_', '-') else '_' for c in execution_record.case_name])
                new_gif_filename = f"{safe_case_name}_{timestamp}.gif"
                new_gif_path = os.path.join(gif_dir, new_gif_filename)

                # 移动并重命名文件
                shutil.move(default_gif_path, new_gif_path)

                # 保存相对路径到数据库（使用正斜杠，确保跨平台兼容）- 使用配置文件中的路径
                # 注意：不要包含 'media/' 前缀，因为 MEDIA_URL 已经是 '/media/'
                relative_path = f'{settings.ALLURE_AI_RECORDING}/{new_gif_filename}'
                execution_record.gif_path = relative_path

                logger.info(f"✅ GIF recording saved to: {relative_path}")
            else:
                logger.warning(f"⚠️ GIF file not found at: {default_gif_path}")
        except Exception as e:
            logger.error(f"❌ Error moving GIF file: {e}")
            logger.warning(f"⚠️ Failed to process GIF recording: {e}")
