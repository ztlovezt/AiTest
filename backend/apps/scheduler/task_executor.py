"""
任务执行器模块
统一管理所有模块的异步任务执行
"""
from django.utils import timezone
from django_q.tasks import async_task
from django_q.models import Schedule
from loguru import logger


def _update_task_stats(schedule_id, success=True):
    """更新任务执行统计"""
    try:
        from apps.scheduler.models import ScheduleConfig
        config = ScheduleConfig.objects.get(schedule__id=schedule_id)
        config.update_stats(success=success)
    except Exception as e:
        logger.error(f"更新任务统计失败: {e}")


def _generate_dingtalk_sign(webhook_url, timestamp):
    """生成钉钉机器人签名"""
    try:
        import urllib.parse
        import base64
        import hmac
        import hashlib
        
        secret = None
        if '&secret=' in webhook_url:
            secret = webhook_url.split('&secret=')[-1].split('&')[0]
        elif '?secret=' in webhook_url:
            secret = webhook_url.split('?secret=')[-1].split('&')[0]
        
        if secret:
            string_to_sign = f'{timestamp}\n{secret}'
            string_to_sign_enc = string_to_sign.encode('utf-8')
            secret_enc = secret.encode('utf-8')
            hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
            sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
            return sign
        return None
    except Exception as e:
        logger.error(f"生成钉钉签名失败: {e}")
        return None


def execute_task(schedule_id):
    """
    执行定时任务
    
    Args:
        schedule_id: Django-Q Schedule ID
        
    Returns:
        任务ID
    """
    try:
        schedule = Schedule.objects.get(id=schedule_id)
    except Schedule.DoesNotExist:
        logger.error(f"调度不存在: {schedule_id}")
        return None
    
    # 检查任务是否被暂停
    try:
        from apps.scheduler.models import ScheduleConfig
        config = ScheduleConfig.objects.get(schedule__id=schedule_id)
        if config.status == 'PAUSED' or not schedule.enabled:
            logger.info(f"任务已暂停，跳过执行: {schedule.name}")
            return None
    except ScheduleConfig.DoesNotExist:
        config = None
    
    group_name = schedule.name
    if config:
        group_name = config.get_module_display()
    
    task_id = async_task(
        'apps.scheduler.task_executor.execute_scheduled_task',
        schedule_id,
        group=group_name
    )
    logger.info(f"任务已提交: {schedule.name}, task_id={task_id}")
    return task_id


def execute_scheduled_task(schedule_id):
    """
    执行定时任务的入口函数
    根据任务类型调用对应的执行器
    
    Args:
        schedule_id: Django-Q Schedule ID
    """
    from apps.scheduler.models import ScheduleConfig
    
    try:
        # 兼容处理：如果 schedule_id 是列表，取第一个元素
        if isinstance(schedule_id, list):
            schedule_id = schedule_id[0] if schedule_id else None
        
        if not schedule_id:
            logger.error("schedule_id 为空")
            return
        
        schedule = Schedule.objects.get(id=schedule_id)
        config = ScheduleConfig.objects.get(schedule__id=schedule_id)
        
        # 检查任务是否被暂停
        if config.status == 'PAUSED' or not schedule.enabled:
            logger.info(f"任务已暂停，跳过执行: {schedule.name}")
            return
    except (Schedule.DoesNotExist, ScheduleConfig.DoesNotExist) as e:
        logger.error(f"获取任务配置失败: {e}")
        return
    
    task_type = config.task_type
    
    if task_type == 'API_TEST_SUITE':
        execute_api_test_suite(schedule_id=schedule_id)
    elif task_type == 'API_REQUEST':
        execute_api_request(schedule_id=schedule_id)
    elif task_type == 'UI_TEST_SUITE':
        execute_ui_test_suite(schedule_id=schedule_id)
    elif task_type == 'UI_TEST_CASE':
        execute_ui_test_cases(schedule_id=schedule_id)
    elif task_type == 'APP_TEST_SUITE':
        execute_app_test_suite(schedule_id=schedule_id)
    elif task_type == 'APP_TEST_CASE':
        execute_app_test_cases(schedule_id=schedule_id)
    else:
        logger.error(f"未知的任务类型: {task_type}")


def execute_api_test_suite(*args, **kwargs):
    """执行API测试套件"""
    from apps.scheduler.models import ScheduleConfig
    from apps.api_testing.models import TestSuite, Environment
    
    schedule_id = None
    try:
        # 优先使用 kwargs 中的 schedule_id（新数据）
        schedule_id = kwargs.get('schedule_id')
        
        # 兼容旧数据：如果 kwargs 中没有 schedule_id，尝试从 args 获取
        if not schedule_id and args:
            schedule_id = args[0]
        
        # 兼容处理：如果 schedule_id 是列表，取第一个元素
        if isinstance(schedule_id, list):
            schedule_id = schedule_id[0] if schedule_id else None
        
        if not schedule_id:
            logger.error("schedule_id 为空")
            return
        
        config = ScheduleConfig.objects.get(schedule__id=schedule_id)
        test_suite = TestSuite.objects.get(id=config.target_id)
        
        environment = None
        if config.environment_id:
            from apps.api_testing.models import Environment
            environment = Environment.objects.get(id=config.environment_id)
        
        logger.info(f"开始执行API测试套件: {test_suite.name}")
        
        from apps.api_testing.utils import execute_test_suite as execute_test_suite_util
        result = execute_test_suite_util(test_suite, environment, config.created_by)
        
        logger.info(f"API测试套件执行完成: {test_suite.name}, 结果: {result}")
        
        # 更新执行统计
        _update_task_stats(schedule_id, success=result.get('success', False))
        
        if config.notify_on_success or config.notify_on_failure:
            send_notification(config, result.get('success', False), result)
        
        # 返回结果以便 Django-Q 记录到 Success 表
        return result
        
    except Exception as e:
        logger.error(f"执行API测试套件失败: {e}", exc_info=True)
        logger.error(f"任务ID: {schedule_id}, 错误类型: {type(e).__name__}")
        # 更新执行统计（失败）
        if schedule_id:
            _update_task_stats(schedule_id, success=False)
        try:
            config = ScheduleConfig.objects.get(schedule__id=schedule_id)
            logger.error(f"任务配置: {config.schedule.name}, 模块: {config.get_module_display()}")
            if config.notify_on_failure:
                send_notification(config, False, {'error': str(e)})
        except Exception as notify_error:
            logger.error(f"发送失败通知时出错: {notify_error}", exc_info=True)
        # 重新抛出异常以便 Django-Q 记录到 Failure 表
        raise


def execute_api_request(*args, **kwargs):
    """执行单个API请求"""
    from apps.scheduler.models import ScheduleConfig
    from apps.api_testing.models import ApiRequest, Environment
    
    schedule_id = None
    try:
        # 优先使用 kwargs 中的 schedule_id（新数据）
        schedule_id = kwargs.get('schedule_id')
        
        # 兼容旧数据：如果 kwargs 中没有 schedule_id，尝试从 args 获取
        if not schedule_id and args:
            schedule_id = args[0]
        
        # 兼容处理：如果 schedule_id 是列表，取第一个元素
        if isinstance(schedule_id, list):
            schedule_id = schedule_id[0] if schedule_id else None
        
        if not schedule_id:
            logger.error("schedule_id 为空")
            return
        
        config = ScheduleConfig.objects.get(schedule__id=schedule_id)
        api_request = ApiRequest.objects.get(id=config.target_id)
        
        environment = None
        if config.environment_id:
            environment = Environment.objects.get(id=config.environment_id)
        
        logger.info(f"开始执行API请求: {api_request.name}")
        
        from apps.api_testing.utils import execute_api_request as execute_api_request_util
        result = execute_api_request_util(api_request, environment, config.created_by)
        
        logger.info(f"API请求执行完成: {api_request.name}")
        
        # 更新执行统计
        _update_task_stats(schedule_id, success=result.get('success', False))
        
        if config.notify_on_success or config.notify_on_failure:
            send_notification(config, result.get('success', False), result)
        
        # 返回结果以便 Django-Q 记录到 Success 表
        return result
        
    except Exception as e:
        logger.error(f"执行API请求失败: {e}", exc_info=True)
        logger.error(f"任务ID: {schedule_id}, 错误类型: {type(e).__name__}")
        # 更新执行统计（失败）
        if schedule_id:
            _update_task_stats(schedule_id, success=False)
        # 重新抛出异常以便 Django-Q 记录到 Failure 表
        raise


def execute_ui_test_suite(*args, **kwargs):
    """执行UI自动化测试套件"""
    from apps.scheduler.models import ScheduleConfig
    from apps.ui_automation.models import TestSuite
    
    schedule_id = None
    try:
        # 优先使用 kwargs 中的 schedule_id（新数据）
        schedule_id = kwargs.get('schedule_id')
        
        # 兼容旧数据：如果 kwargs 中没有 schedule_id，尝试从 args 获取
        if not schedule_id and args:
            schedule_id = args[0]
        
        # 兼容处理：如果 schedule_id 是列表，取第一个元素
        if isinstance(schedule_id, list):
            schedule_id = schedule_id[0] if schedule_id else None
        
        if not schedule_id:
            logger.error("schedule_id 为空")
            return
        
        config = ScheduleConfig.objects.get(schedule__id=schedule_id)
        test_suite = TestSuite.objects.get(id=config.target_id)
        
        task_config = config.task_config or {}
        
        logger.info(f"开始执行UI测试套件: {test_suite.name}")
        
        from apps.ui_automation.test_executor import TestExecutor
        executor = TestExecutor(
            test_suite=test_suite,
            engine=task_config.get('engine', 'playwright'),
            browser=task_config.get('browser', 'chrome'),
            headless=task_config.get('headless', True),
            executed_by=config.created_by
        )
        executor.run()
        
        logger.info(f"UI测试套件执行完成: {test_suite.name}")
        
        # 更新执行统计
        _update_task_stats(schedule_id, success=True)
        
        if config.notify_on_success or config.notify_on_failure:
            send_notification(config, True, {})
        
        # 返回结果以便 Django-Q 记录到 Success 表
        return {'success': True, 'message': 'UI测试套件执行完成'}
        
    except Exception as e:
        logger.error(f"执行UI测试套件失败: {e}", exc_info=True)
        logger.error(f"任务ID: {schedule_id}, 错误类型: {type(e).__name__}")
        # 更新执行统计（失败）
        if schedule_id:
            _update_task_stats(schedule_id, success=False)
        try:
            config = ScheduleConfig.objects.get(schedule__id=schedule_id)
            logger.error(f"任务配置: {config.schedule.name}, 模块: {config.get_module_display()}")
            if config.notify_on_failure:
                send_notification(config, False, {'error': str(e)})
        except Exception as notify_error:
            logger.error(f"发送失败通知时出错: {notify_error}", exc_info=True)
        # 重新抛出异常以便 Django-Q 记录到 Failure 表
        raise


def execute_ui_test_cases(*args, **kwargs):
    """执行UI自动化测试用例"""
    from apps.scheduler.models import ScheduleConfig
    from apps.ui_automation.models import TestCase as UiTestCase, TestSuite
    
    schedule_id = None
    try:
        # 优先使用 kwargs 中的 schedule_id（新数据）
        schedule_id = kwargs.get('schedule_id')
        
        # 兼容旧数据：如果 kwargs 中没有 schedule_id，尝试从 args 获取
        if not schedule_id and args:
            schedule_id = args[0]
        
        # 兼容处理：如果 schedule_id 是列表，取第一个元素
        if isinstance(schedule_id, list):
            schedule_id = schedule_id[0] if schedule_id else None
        
        if not schedule_id:
            logger.error("schedule_id 为空")
            return
        
        config = ScheduleConfig.objects.get(schedule__id=schedule_id)
        task_config = config.task_config or {}
        test_case_ids = task_config.get('test_case_ids', [])
        
        test_cases = UiTestCase.objects.filter(id__in=test_case_ids)
        
        logger.info(f"开始执行UI测试用例: {len(test_case_ids)} 个")
        
        for test_case in test_cases:
            temp_suite = TestSuite.objects.create(
                project=test_case.project,
                name=f"[定时任务] {test_case.name}"
            )
            temp_suite.test_cases.add(test_case)
            
            from apps.ui_automation.test_executor import TestExecutor
            executor = TestExecutor(
                test_suite=temp_suite,
                engine=task_config.get('engine', 'playwright'),
                browser=task_config.get('browser', 'chrome'),
                headless=task_config.get('headless', True),
                executed_by=config.created_by
            )
            executor.run()
        
        logger.info(f"UI测试用例执行完成")
        
        # 更新执行统计
        _update_task_stats(schedule_id, success=True)
        
        # 返回结果以便 Django-Q 记录到 Success 表
        return {'success': True, 'message': 'UI测试用例执行完成'}
        
    except Exception as e:
        logger.error(f"执行UI测试用例失败: {e}", exc_info=True)
        logger.error(f"任务ID: {schedule_id}, 错误类型: {type(e).__name__}")
        # 更新执行统计（失败）
        if schedule_id:
            _update_task_stats(schedule_id, success=False)
        # 重新抛出异常以便 Django-Q 记录到 Failure 表
        raise


def execute_app_test_suite(*args, **kwargs):
    """执行APP自动化测试套件"""
    from apps.scheduler.models import ScheduleConfig
    from apps.app_automation.models import AppTestSuite
    
    schedule_id = None
    try:
        # 优先使用 kwargs 中的 schedule_id（新数据）
        schedule_id = kwargs.get('schedule_id')
        
        # 兼容旧数据：如果 kwargs 中没有 schedule_id，尝试从 args 获取
        if not schedule_id and args:
            schedule_id = args[0]
        
        # 兼容处理：如果 schedule_id 是列表，取第一个元素
        if isinstance(schedule_id, list):
            schedule_id = schedule_id[0] if schedule_id else None
        
        if not schedule_id:
            logger.error("schedule_id 为空")
            return
        
        config = ScheduleConfig.objects.get(schedule__id=schedule_id)
        test_suite = AppTestSuite.objects.get(id=config.target_id)
        
        task_config = config.task_config or {}
        
        logger.info(f"开始执行APP测试套件: {test_suite.name}")
        
        from apps.app_automation.executors.test_executor import AppTestExecutor
        executor = AppTestExecutor()
        result = executor.run_tests(
            test_case_id=test_suite.id,
            device_id=task_config.get('device_id'),
            package_name=task_config.get('app_package_name', ''),
            execution_id=None,
            username=config.created_by.username if config.created_by else None
        )
        
        logger.info(f"APP测试套件执行完成: {test_suite.name}")
        
        # 更新执行统计
        _update_task_stats(schedule_id, success=True)
        
        # 返回结果以便 Django-Q 记录到 Success 表
        return {'success': True, 'message': 'APP测试套件执行完成'}
        
    except Exception as e:
        logger.error(f"执行APP测试套件失败: {e}", exc_info=True)
        logger.error(f"任务ID: {schedule_id}, 错误类型: {type(e).__name__}")
        # 更新执行统计（失败）
        if schedule_id:
            _update_task_stats(schedule_id, success=False)
        # 重新抛出异常以便 Django-Q 记录到 Failure 表
        raise


def execute_app_test_cases(*args, **kwargs):
    """执行APP自动化测试用例"""
    from apps.scheduler.models import ScheduleConfig
    from apps.app_automation.models import AppTestCase, AppTestSuite
    
    schedule_id = None
    try:
        # 优先使用 kwargs 中的 schedule_id（新数据）
        schedule_id = kwargs.get('schedule_id')
        
        # 兼容旧数据：如果 kwargs 中没有 schedule_id，尝试从 args 获取
        if not schedule_id and args:
            schedule_id = args[0]
        
        # 兼容处理：如果 schedule_id 是列表，取第一个元素
        if isinstance(schedule_id, list):
            schedule_id = schedule_id[0] if schedule_id else None
        
        if not schedule_id:
            logger.error("schedule_id 为空")
            return
        
        config = ScheduleConfig.objects.get(schedule__id=schedule_id)
        task_config = config.task_config or {}
        test_case_ids = task_config.get('test_case_ids', [])
        
        test_cases = AppTestCase.objects.filter(id__in=test_case_ids)
        
        logger.info(f"开始执行APP测试用例: {len(test_case_ids)} 个")
        
        for test_case in test_cases:
            temp_suite = AppTestSuite.objects.create(
                project=test_case.project,
                name=f"[定时任务] {test_case.name}"
            )
            temp_suite.test_cases.add(test_case)
            
            from apps.app_automation.executors.test_executor import AppTestExecutor
            executor = AppTestExecutor(
                test_suite=temp_suite,
                device_id=task_config.get('device_id'),
                executed_by=config.created_by
            )
            executor.run()
        
        logger.info(f"APP测试用例执行完成")
        
        # 更新执行统计
        _update_task_stats(schedule_id, success=True)
        
        # 返回结果以便 Django-Q 记录到 Success 表
        return {'success': True, 'message': 'APP测试用例执行完成'}
        
    except Exception as e:
        logger.error(f"执行APP测试用例失败: {e}", exc_info=True)
        logger.error(f"任务ID: {schedule_id}, 错误类型: {type(e).__name__}")
        # 更新执行统计（失败）
        if schedule_id:
            _update_task_stats(schedule_id, success=False)
        # 重新抛出异常以便 Django-Q 记录到 Failure 表
        raise


def _render_notification_template(template_content, context):
    """渲染通知模板
    
    Args:
        template_content: 模板内容（Markdown格式）
        context: 上下文变量字典
        
    Returns:
        str: 渲染后的内容
    """
    content = template_content
    for key, value in context.items():
        placeholder = f"{{{{{key}}}}}"
        content = content.replace(placeholder, str(value) if value is not None else '')
    return content


def _build_notification_context(config, success, result):
    """构建通知模板上下文变量
    
    Args:
        config: ScheduleConfig 实例
        success: 是否成功
        result: 执行结果
        
    Returns:
        dict: 上下文变量字典
    """
    status_text = '成功' if success else '失败'
    now = timezone.now()
    
    context = {
        'title': f'定时任务执行{status_text}',
        'task_name': config.schedule.name if config.schedule else 'Unknown',
        'task_type': config.get_task_type_display(),
        'module': config.get_module_display(),
        'status': status_text,
        'execution_time': now.strftime('%Y-%m-%d %H:%M:%S'),
        'success': '是' if success else '否',
        'start_time': now.strftime('%Y-%m-%d %H:%M:%S'),
        'end_time': now.strftime('%Y-%m-%d %H:%M:%S'),
    }
    
    if result:
        if isinstance(result, dict):
            total_cases = result.get('total_count', result.get('total_cases', 0))
            passed_cases = result.get('passed_count', result.get('passed_cases', 0))
            failed_cases = result.get('failed_count', result.get('failed_cases', 0))
            error_cases = result.get('error_count', result.get('error_cases', 0))
            skipped_cases = result.get('skipped_count', result.get('skipped_cases', 0))
            
            context['total_cases'] = total_cases
            context['passed_cases'] = passed_cases
            context['failed_cases'] = failed_cases
            context['error_cases'] = error_cases
            context['skipped_cases'] = skipped_cases
            
            if total_cases > 0:
                pass_rate = (passed_cases / total_cases) * 100
                context['pass_rate'] = f"{pass_rate:.2f}%"
                coverage_rate = ((passed_cases + failed_cases) / total_cases) * 100
                context['coverage_rate'] = f"{coverage_rate:.2f}%"
            else:
                context['pass_rate'] = "0%"
                context['coverage_rate'] = "0%"
            
            if 'duration' in result:
                duration_seconds = float(result['duration'])
                minutes = int(duration_seconds // 60)
                seconds = int(duration_seconds % 60)
                context['duration'] = f"{minutes}分{seconds}秒" if minutes > 0 else f"{seconds}秒"
    
    if config.project_id:
        try:
            from apps.projects.models import Project
            project = Project.objects.get(id=config.project_id)
            context['project_name'] = project.name
        except Exception:
            context['project_name'] = ''
    
    if config.environment_id:
        try:
            from apps.api_testing.models import Environment
            env = Environment.objects.get(id=config.environment_id)
            context['environment_name'] = env.name
        except Exception:
            context['environment_name'] = ''
    
    if config.created_by:
        context['creator'] = config.created_by.username
        if hasattr(config.created_by, 'get_full_name') and config.created_by.get_full_name():
            context['creator'] = config.created_by.get_full_name()
    
    # 执行人默认为系统
    context['executor'] = '系统自动执行'
    
    try:
        from django.conf import settings
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        if config.schedule:
            context['report_url'] = f"{frontend_url}/reports/schedule/{config.schedule.id}"
    except Exception:
        pass
    
    return context


def send_notification(config, success, result):
    """
    发送任务执行通知
    
    Args:
        config: ScheduleConfig 实例
        success: 是否成功
        result: 执行结果
    """
    import requests
    import json
    
    if success and not config.notify_on_success:
        return
    if not success and not config.notify_on_failure:
        return
    
    status_text = '成功' if success else '失败'
    context = _build_notification_context(config, success, result)
    
    logger.info(f"=== 开始发送任务通知 ===")
    logger.info(f"任务名称: {config.schedule.name if config.schedule else 'Unknown'}")
    logger.info(f"通知设置 - 成功通知: {config.notify_on_success}, 失败通知: {config.notify_on_failure}")
    logger.info(f"通知类型 - 邮件通知: {config.notify_on_email}, Webhook通知: {config.notify_on_webhook}")
    logger.info(f"通知配置数量: {config.notification_configs.count()}")
    logger.info(f"通知配置列表: {list(config.notification_configs.values_list('id', 'name'))}")
    logger.info(f"通知邮箱: {config.notify_emails}")
    
    # 根据通知类型决定发送哪种通知
    should_send_email = config.notify_on_email and config.notify_emails and len(config.notify_emails) > 0
    should_send_webhook = config.notify_on_webhook and config.notification_configs.exists()
    
    logger.info(f"发送邮件通知: {should_send_email}")
    logger.info(f"发送Webhook通知: {should_send_webhook}")
    
    # 发送Webhook通知
    if should_send_webhook:
        try:
            from apps.core.models import UnifiedNotificationConfig
            from services.notification_tasks import send_webhook_notification_task
            
            # 使用配置的通知配置
            configured_webhook_configs = config.notification_configs.filter(
                config_type__in=['webhook_wechat', 'webhook_feishu', 'webhook_dingtalk', 'webhook_generic'],
                is_active=True
            )
            logger.info(f"使用配置的通知配置 (notification_configs), 找到 {configured_webhook_configs.count()} 个webhook配置")
            logger.info(f"webhook配置列表: {list(configured_webhook_configs.values_list('id', 'name', 'config_type'))}")
            
            all_webhook_bots = []
            for webhook_config in configured_webhook_configs:
                bots = webhook_config.get_webhook_bots()
                logger.info(f"配置 {webhook_config.name} 的机器人列表: {bots}")
                if bots:
                    for bot in bots:
                        if bot.get('enabled', True):
                            module = config.module
                            if module == 'API' and bot.get('enable_api_testing', True):
                                all_webhook_bots.append(bot)
                                logger.info(f"添加机器人: {bot.get('name')} (API测试已启用)")
                            elif module == 'UI' and bot.get('enable_ui_automation', True):
                                all_webhook_bots.append(bot)
                                logger.info(f"添加机器人: {bot.get('name')} (UI自动化测试已启用)")
                            elif module == 'APP' and bot.get('enable_app_automation', True):
                                all_webhook_bots.append(bot)
                                logger.info(f"添加机器人: {bot.get('name')} (APP自动化测试已启用)")
                            else:
                                logger.info(f"配置中心机器人 {bot.get('name')} 未启用{module}测试，跳过")
            
            if not all_webhook_bots:
                logger.warning("没有找到任何启用的webhook机器人配置")
            else:
                logger.info(f"找到 {len(all_webhook_bots)} 个启用的webhook机器人配置")
                
                for bot in all_webhook_bots:
                    if not bot.get('enabled', True) or not bot.get('webhook_url'):
                        continue
                    
                    webhook_url = bot['webhook_url'].strip().strip('`').strip()
                    bot_type = bot.get('type', '')
                    template_id = bot.get('notification_template_id')
                    
                    template_content = None
                    if template_id:
                        try:
                            from apps.core.models import NotificationTemplate
                            template = NotificationTemplate.objects.get(id=template_id)
                            template_content = template.content
                            logger.info(f"使用自定义模板: {template.name}")
                        except NotificationTemplate.DoesNotExist:
                            logger.warning(f"模板不存在: {template_id}")
                    
                    if template_content:
                        rendered_content = _render_notification_template(template_content, context)
                    else:
                        rendered_content = f"""**定时任务执行{status_text}**

任务名称: {context['task_name']}

执行状态: {status_text}

执行时间: {context['execution_time']}

任务类型: {context['task_type']}"""
                    
                    message_data = None
                    if bot_type == 'wechat':
                        message_data = {
                            "msgtype": "markdown",
                            "markdown": {
                                "content": rendered_content
                            }
                        }
                    elif bot_type == 'feishu':
                        message_data = {
                            "msg_type": "interactive",
                            "card": {
                                "elements": [{
                                    "tag": "div",
                                    "text": {
                                        "content": rendered_content.replace('\n\n', '\n'),
                                        "tag": "lark_md"
                                    }
                                }],
                                "header": {
                                    "title": {
                                        "content": f"定时任务执行{status_text}",
                                        "tag": "plain_text"
                                    },
                                    "template": "green" if success else "red"
                                }
                            }
                        }
                    elif bot_type == 'dingtalk':
                        message_data = {
                            "msgtype": "markdown",
                            "markdown": {
                                "title": f"定时任务执行{status_text}",
                                "text": rendered_content
                            }
                        }
                        
                        # 钉钉机器人签名验证
                        secret = bot.get('secret')
                        if secret:
                            import time
                            import hmac
                            import hashlib
                            import base64
                            import urllib.parse

                            timestamp = str(round(time.time() * 1000))
                            string_to_sign = f'{timestamp}\n{secret}'
                            string_to_sign_enc = string_to_sign.encode('utf-8')
                            secret_enc = secret.encode('utf-8')
                            hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
                            sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))

                            # 在URL中添加签名参数
                            if '?' in webhook_url:
                                webhook_url += f'&timestamp={timestamp}&sign={sign}'
                            else:
                                webhook_url += f'?timestamp={timestamp}&sign={sign}'

                            logger.info(f"钉钉机器人签名验证 - 时间戳: {timestamp}")
                            logger.info(f"签名字符串: {string_to_sign}")
                            logger.info(f"生成的签名: {sign}")
                            logger.info(f"最终URL: {webhook_url}")
                        else:
                            logger.info(f"钉钉机器人未配置签名密钥，使用无签名模式")
                    else:
                        message_data = {
                            "text": rendered_content
                        }
                    
                    try:
                        # 根据模块设置分组
                        group = config.get_module_display()
                        send_webhook_notification_task(
                            webhook_url=webhook_url,
                            message=message_data,
                            bot_type=f'webhook_{bot_type}',
                            group=group
                        )
                        logger.info(f"Webhook通知任务已加入队列: {bot_type} - {webhook_url}")
                    except Exception as e:
                        logger.error(f"发送webhook请求失败: {str(e)}")
                        logger.error(f"Webhook URL: {webhook_url}")
        except ImportError as e:
            logger.error(f"无法导入统一通知配置: {e}")
        except Exception as e:
            logger.error(f"发送Webhook通知失败: {e}")
    
    # 发送邮件通知
    if should_send_email:
        from services.email_tasks import send_task_notification_task
        
        status = 'success' if success else 'failed'
        task_name = config.schedule.name if config.schedule else 'Unknown'
        task_type = f"{config.get_module_display()}-{config.get_task_type_display()}"
        execution_time = str(timezone.now())
        
        try:
            send_task_notification_task(
                task_name,
                task_type,
                status,
                config.notify_emails,
                "",
                execution_time,
                result
            )
            logger.info(f"邮件通知任务已加入队列: {config.notify_emails}")
        except Exception as e:
            logger.error(f"发送邮件通知失败: {e}")
