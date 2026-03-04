"""
任务执行器模块
统一管理所有模块的异步任务执行
"""
from django.utils import timezone
from django_q.tasks import async_task
from django_q.models import Schedule
from loguru import logger


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
        pass
    
    # 获取所属模块作为group
    group_name = schedule.name
    try:
        config = ScheduleConfig.objects.get(schedule__id=schedule_id)
        group_name = config.get_module_display()
    except Exception:
        pass
    
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
        
        if config.notify_on_success or config.notify_on_failure:
            send_notification(config, result.get('success', False), result)
        
        # 返回结果以便 Django-Q 记录到 Success 表
        return result
        
    except Exception as e:
        logger.error(f"执行API测试套件失败: {e}", exc_info=True)
        logger.error(f"任务ID: {schedule_id}, 错误类型: {type(e).__name__}")
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
        
        if config.notify_on_success or config.notify_on_failure:
            send_notification(config, result.get('success', False), result)
        
        # 返回结果以便 Django-Q 记录到 Success 表
        return result
        
    except Exception as e:
        logger.error(f"执行API请求失败: {e}", exc_info=True)
        logger.error(f"任务ID: {schedule_id}, 错误类型: {type(e).__name__}")
        # 重新抛出异常以便 Django-Q 记录到 Failure 表
        raise


def execute_ui_test_suite(*args, **kwargs):
    """执行UI自动化测试套件"""
    from apps.scheduler.models import ScheduleConfig
    from apps.ui_automation.models import TestSuite
    
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
        
        if config.notify_on_success or config.notify_on_failure:
            send_notification(config, True, {})
        
        # 返回结果以便 Django-Q 记录到 Success 表
        return {'success': True, 'message': 'UI测试套件执行完成'}
        
    except Exception as e:
        logger.error(f"执行UI测试套件失败: {e}", exc_info=True)
        logger.error(f"任务ID: {schedule_id}, 错误类型: {type(e).__name__}")
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
        
        # 返回结果以便 Django-Q 记录到 Success 表
        return {'success': True, 'message': 'UI测试用例执行完成'}
        
    except Exception as e:
        logger.error(f"执行UI测试用例失败: {e}", exc_info=True)
        logger.error(f"任务ID: {schedule_id}, 错误类型: {type(e).__name__}")
        # 重新抛出异常以便 Django-Q 记录到 Failure 表
        raise


def execute_app_test_suite(*args, **kwargs):
    """执行APP自动化测试套件"""
    from apps.scheduler.models import ScheduleConfig
    from apps.app_automation.models import AppTestSuite
    
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
        
        # 返回结果以便 Django-Q 记录到 Success 表
        return {'success': True, 'message': 'APP测试套件执行完成'}
        
    except Exception as e:
        logger.error(f"执行APP测试套件失败: {e}", exc_info=True)
        logger.error(f"任务ID: {schedule_id}, 错误类型: {type(e).__name__}")
        # 重新抛出异常以便 Django-Q 记录到 Failure 表
        raise


def execute_app_test_cases(*args, **kwargs):
    """执行APP自动化测试用例"""
    from apps.scheduler.models import ScheduleConfig
    from apps.app_automation.models import AppTestCase, AppTestSuite
    
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
        
        # 返回结果以便 Django-Q 记录到 Success 表
        return {'success': True, 'message': 'APP测试用例执行完成'}
        
    except Exception as e:
        logger.error(f"执行APP测试用例失败: {e}", exc_info=True)
        logger.error(f"任务ID: {schedule_id}, 错误类型: {type(e).__name__}")
        # 重新抛出异常以便 Django-Q 记录到 Failure 表
        raise


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
    
    message = {
        'task_name': config.schedule.name if config.schedule else 'Unknown',
        'module': config.get_module_display(),
        'task_type': config.get_task_type_display(),
        'success': success,
        'result': result,
        'time': str(timezone.now()),
    }
    
    if config.use_webhook:
        try:
            from apps.core.models import UnifiedNotificationConfig
            
            all_webhook_configs = UnifiedNotificationConfig.objects.filter(
                config_type__in=['webhook_wechat', 'webhook_feishu', 'webhook_dingtalk'],
                is_active=True
            )
            logger.info("使用统一通知配置 (UnifiedNotificationConfig)")
            
            all_webhook_bots = []
            for webhook_config in all_webhook_configs:
                bots = webhook_config.get_webhook_bots()
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
                    
                    webhook_url = bot['webhook_url']
                    bot_type = bot.get('type', '')
                    
                    try:
                        if bot_type == 'webhook_dingtalk':
                            timestamp = str(int(timezone.now().timestamp() * 1000))
                            sign = _generate_dingtalk_sign(webhook_url, timestamp)
                            if '?' in webhook_url:
                                webhook_url += f'&timestamp={timestamp}&sign={sign}'
                            else:
                                webhook_url += f'?timestamp={timestamp}&sign={sign}'
                        
                        logger.info(f"发送请求到: {webhook_url}")
                        
                        response = requests.post(
                            webhook_url,
                            json=message,
                            headers={'Content-Type': 'application/json'},
                            timeout=10
                        )
                        
                        logger.info(f"Webhook通知发送成功 - {bot_type}: {response.status_code}")
                    except Exception as e:
                        logger.error(f"发送webhook请求失败: {str(e)}")
                        logger.error(f"Webhook URL: {webhook_url}")
        except ImportError as e:
            logger.error(f"无法导入统一通知配置: {e}")
        except Exception as e:
            logger.error(f"发送Webhook通知失败: {e}")
    
    if config.notify_emails:
        from django.core.mail import send_mail
        from django.conf import settings
        
        subject = f"[TestHub] 任务执行{'成功' if success else '失败'}: {config.schedule.name if config.schedule else 'Unknown'}"
        body = f"""
任务名称: {config.schedule.name if config.schedule else 'Unknown'}
所属模块: {config.get_module_display()}
任务类型: {config.get_task_type_display()}
执行状态: {'成功' if success else '失败'}
执行时间: {timezone.now()}
结果: {result}
        """
        
        try:
            send_mail(
                subject,
                body,
                settings.DEFAULT_FROM_EMAIL,
                config.notify_emails,
                fail_silently=False,
            )
            logger.info(f"邮件通知已发送: {config.notify_emails}")
        except Exception as e:
            logger.error(f"发送邮件通知失败: {e}")
