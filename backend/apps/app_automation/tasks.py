# -*- coding: utf-8 -*-
"""
APP自动化测试任务

注意：定时任务通知功能已迁移到 apps.scheduler.task_executor 模块统一处理
"""
from django.utils import timezone
import logging
import os
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


def send_execution_update(execution_id, status=None, progress=None, message=None, report_path=None, finished_at=None, result=None):
    """通过 WebSocket 发送执行状态更新"""
    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
            return
        payload = {
            "type": "execution_update",
            "execution_id": int(execution_id),
            "status": status,
            "result": result,
            "progress": progress,
            "message": message,
            "report_path": report_path,
            "finished_at": finished_at.isoformat() if finished_at else None,
        }
        async_to_sync(channel_layer.group_send)(
            f"app_execution_{execution_id}",
            payload
        )
    except Exception as e:
        logger.debug(f"发送执行状态更新失败: {e}")


def execute_app_test_task(execution_id, package_name: str = None, scheduled_task_id: int = None):
    """
    异步执行APP测试任务
    
    Args:
        execution_id: AppTestExecution 的 ID
        package_name: 可选的应用包名
        scheduled_task_id: 可选的定时任务 ID（来自定时调度）
    """
    from django.conf import settings
    from .models import AppTestExecution, AppDevice
    from .executors.test_executor import AppTestExecutor
    
    execution = None
    device = None
    
    try:
        # 获取执行记录
        execution = AppTestExecution.objects.get(id=execution_id)
        test_case = execution.test_case
        
        device = execution.device
        
        # 更新状态为执行中
        execution.status = 'running'
        execution.started_at = timezone.now()
        execution.progress = 0
        execution.save()
        send_execution_update(execution_id, status='running', progress=0, message='任务开始执行')
        
        logger.info(f"开始执行APP测试: {test_case.name}")
        
        # 1. 检查并锁定设备
        if device.is_locked_for_user(execution.user):
            raise RuntimeError(f"设备 {device.device_id} 已被其他用户锁定")
        
        if not (
            device.is_locked_by_user(execution.user)
            and device.lock_type == device.LOCK_TYPE_AUTOMATION
            and device.lock_session_id == f'automation:{execution.id}'
        ):
            device.lock_for_automation(execution.user, execution.id)
        
        logger.info(f"设备已锁定: {device.device_id}")
        
        # 2. 由 pytest + allure 插件执行测试
        # 进度分配：0~10% 环境准备，10~90% 步骤执行（由子进程内回调动态更新），90~100% 报告生成
        execution.progress = 10
        execution.save()
        send_execution_update(execution_id, status='running', progress=10, message='正在准备测试环境')
        
        if package_name:
            final_package_name = package_name
        else:
            final_package_name = test_case.app_package.package_name if test_case.app_package else ""

        executor = AppTestExecutor()
        report_result = executor.run_tests(
            test_case_id=test_case.id,
            device_id=device.device_id,
            package_name=final_package_name,
            execution_id=execution_id,
            username=execution.user.username if execution.user else 'unknown',
        )
        
        # 从数据库重新读取最新进度（子进程中的回调可能已经更新过）
        execution.refresh_from_db()
        
        if report_result.get('report_path'):
            execution.report_path = report_result['report_path']
            logger.info(f"报告已生成: {report_result['report_path']}")
        
        test_results = report_result.get('test_results', {})
        execution.total_steps = test_results.get('total', 0)
        execution.passed_steps = test_results.get('passed', 0)
        execution.failed_steps = test_results.get('failed', 0)
        execution.skipped_steps = test_results.get('skipped', 0)
        
        if report_result.get('result_data'):
            execution.result_data = report_result['result_data']
        
        execution.progress = 95
        execution.save()
        send_execution_update(
            execution_id,
            status='running',
            progress=95,
            message='正在生成测试报告',
            report_path=execution.report_path
        )
        
        # 3. 完成测试 — 分离任务状态和测试结果
        execution.status = 'completed'
        if execution.total_steps == 0:
            execution.result = 'skipped'
        elif execution.failed_steps == 0:
            execution.result = 'passed'
        else:
            execution.result = 'failed'
        execution.finished_at = timezone.now()
        execution.duration = (execution.finished_at - execution.started_at).total_seconds()
        execution.progress = 100
        execution.save()
        send_execution_update(
            execution_id,
            status=execution.status,
            progress=100,
            message='执行完成',
            report_path=execution.report_path,
            finished_at=execution.finished_at,
            result=execution.result,
        )
        
        logger.info(f"APP测试执行完成: {test_case.name}, 状态: {execution.status}, 结果: {execution.result}")

    except AppTestExecution.DoesNotExist:
        logger.error(f"执行记录不存在: {execution_id}")
    except Exception as e:
        logger.error(f"执行APP测试失败: {str(e)}", exc_info=True)
        
        if execution:
            execution.status = 'error'       # 任务异常（非用例失败）
            execution.result = None           # 没有测试结果
            execution.error_message = str(e)
            execution.finished_at = timezone.now()
            if execution.started_at:
                execution.duration = (execution.finished_at - execution.started_at).total_seconds()
            execution.save()
            send_execution_update(
                execution_id,
                status='error',
                progress=execution.progress or 0,
                message=str(e),
                report_path=execution.report_path,
                finished_at=execution.finished_at,
                result=None,
            )
            
            # 尝试生成报告
            try:
                executor = AppTestExecutor()
                executor._generate_allure_report(execution_id=execution_id)
            except Exception:
                pass
    finally:
        # 7. 清理：释放设备
        try:
            if device:
                device.unlock(session_id=f'automation:{execution.id}')
                logger.info(f"设备已释放: {device.device_id}")
        except Exception as e:
            logger.error(f"释放设备失败: {str(e)}")


def execute_app_suite_task(suite_id, execution_ids, package_name=None, scheduled_task_id=None):
    """
    异步执行APP测试套件（顺序执行多个用例）

    Args:
        suite_id: AppTestSuite 的 ID
        execution_ids: AppTestExecution ID 列表（按执行顺序）
        package_name: 可选的应用包名覆盖
        scheduled_task_id: 可选的定时任务 ID
    """
    from .models import AppTestSuite, AppTestExecution, AppDevice
    from .executors.test_executor import AppTestExecutor

    suite = None
    device = None
    passed = 0
    failed = 0

    try:
        suite = AppTestSuite.objects.get(id=suite_id)
        executions = list(
            AppTestExecution.objects.filter(id__in=execution_ids)
            .select_related('test_case', 'test_case__app_package', 'device', 'user')
            .order_by('id')
        )
        # 按 execution_ids 排序
        exec_map = {e.id: e for e in executions}
        executions = [exec_map[eid] for eid in execution_ids if eid in exec_map]

        if not executions:
            logger.error(f"套件 {suite_id} 未找到执行记录")
            return

        device = executions[0].device
        user = executions[0].user

        # 锁定设备
        if device.is_locked_for_user(user):
            raise RuntimeError(f"设备 {device.device_id} 已被其他用户锁定")
        if not (
            device.is_locked_by_user(user)
            and device.lock_type == device.LOCK_TYPE_AUTOMATION
            and device.lock_session_id == f'automation:suite:{suite_id}'
        ):
            device.lock_for_automation(user, f'suite:{suite_id}')
        logger.info(f"套件执行开始: {suite.name}, 设备: {device.device_id}, 共 {len(executions)} 个用例")

        for idx, execution in enumerate(executions):
            test_case = execution.test_case
            if not test_case:
                execution.status = 'error'
                execution.result = None
                execution.error_message = '用例不存在'
                execution.finished_at = timezone.now()
                execution.save()
                failed += 1
                continue

            try:
                # 更新为运行中
                execution.status = 'running'
                execution.started_at = timezone.now()
                execution.progress = 0
                execution.save()
                send_execution_update(
                    execution.id, status='running', progress=0,
                    message=f'开始执行 ({idx + 1}/{len(executions)})'
                )

                # 确定包名
                if package_name:
                    final_pkg = package_name
                else:
                    final_pkg = test_case.app_package.package_name if test_case.app_package else ""

                execution.progress = 10
                execution.save()
                send_execution_update(
                    execution.id, status='running', progress=10,
                    message='正在准备测试环境'
                )

                executor = AppTestExecutor()
                report_result = executor.run_tests(
                    test_case_id=test_case.id,
                    device_id=device.device_id,
                    package_name=final_pkg,
                    execution_id=execution.id,
                    username=execution.user.username if execution.user else 'unknown',
                )

                execution.refresh_from_db()

                if report_result.get('report_path'):
                    execution.report_path = report_result['report_path']

                test_results = report_result.get('test_results', {})
                execution.total_steps = test_results.get('total', 0)
                execution.passed_steps = test_results.get('passed', 0)
                execution.failed_steps = test_results.get('failed', 0)
                execution.skipped_steps = test_results.get('skipped', 0)
                
                if report_result.get('result_data'):
                    execution.result_data = report_result['result_data']

                execution.status = 'completed'
                if execution.total_steps == 0:
                    execution.result = 'skipped'
                elif execution.failed_steps == 0:
                    execution.result = 'passed'
                else:
                    execution.result = 'failed'
                execution.finished_at = timezone.now()
                execution.duration = (execution.finished_at - execution.started_at).total_seconds()
                execution.progress = 100
                execution.save()

                if execution.result == 'passed':
                    passed += 1
                else:
                    failed += 1

                send_execution_update(
                    execution.id, status=execution.status, progress=100,
                    message='执行完成',
                    report_path=execution.report_path,
                    finished_at=execution.finished_at,
                    result=execution.result,
                )

                logger.info(f"用例 {test_case.name} 执行完成: status={execution.status}, result={execution.result}")

            except Exception as e:
                logger.error(f"用例 {test_case.name} 执行失败: {str(e)}", exc_info=True)
                execution.status = 'error'
                execution.result = None
                execution.error_message = str(e)
                execution.finished_at = timezone.now()
                if execution.started_at:
                    execution.duration = (execution.finished_at - execution.started_at).total_seconds()
                execution.save()
                failed += 1
                send_execution_update(
                    execution.id, status='error',
                    progress=execution.progress or 0,
                    message=str(e),
                    finished_at=execution.finished_at,
                    result=None,
                )

        # 更新套件统计
        suite.execution_status = 'completed'
        if passed == 0 and failed == 0:
            suite.execution_result = 'skipped'
        elif failed == 0:
            suite.execution_result = 'passed'
        else:
            suite.execution_result = 'failed'
        suite.passed_count = passed
        suite.failed_count = failed
        suite.last_run_at = timezone.now()
        suite.save(update_fields=['execution_status', 'execution_result', 'passed_count', 'failed_count', 'last_run_at'])

        logger.info(f"套件执行完成: {suite.name}, 通过: {passed}, 失败: {failed}")

    except AppTestSuite.DoesNotExist:
        logger.error(f"测试套件不存在: {suite_id}")
    except Exception as e:
        logger.error(f"执行套件失败: {str(e)}", exc_info=True)
        if suite:
            suite.execution_status = 'error'
            suite.execution_result = None
            suite.failed_count = failed
            suite.passed_count = passed
            suite.last_run_at = timezone.now()
            suite.save(update_fields=['execution_status', 'execution_result', 'passed_count', 'failed_count', 'last_run_at'])
    finally:
        # 释放设备
        try:
            if device:
                device.refresh_from_db()
                device.unlock(session_id=f'automation:suite:{suite_id}')
                logger.info(f"设备已释放: {device.device_id}")
        except Exception as e:
            logger.error(f"释放设备失败: {str(e)}")


def check_and_release_expired_devices():
    """
    检查并释放过期锁定的设备
    """
    from .models import AppDevice
    
    try:
        devices = AppDevice.objects.filter(status='locked')
        released_count = 0
        
        for device in devices:
            if device.is_lock_expired():
                device.unlock(force=True)
                released_count += 1
                logger.info(f"释放过期锁定的设备: {device.device_id}")
        
        logger.info(f"检查设备锁定完成，释放 {released_count} 个设备")
        
    except Exception as e:
        logger.error(f"检查设备锁定失败: {str(e)}", exc_info=True)


def check_device_status_task():
    """
    定期检查设备状态并更新数据库
    
    功能：
    1. 通过 ADB 获取当前连接的设备列表
    2. 更新在线设备状态为 available（如果未被锁定）
    3. 将不在 ADB 列表中的设备标记为 offline（保持 locked 状态不变）
    
    建议配置：每 5-10 分钟执行一次
    """
    from .models import AppDevice
    from .managers.device_manager import DeviceManager
    
    logger.info("开始检查设备状态...")
    
    try:
        # 获取 ADB 路径
        try:
            from .models import AppTestConfig
            config = AppTestConfig.objects.first()
            adb_path = config.adb_path if config else 'adb'
        except Exception as e:
            logger.warning(f"获取 ADB 配置失败，使用默认路径: {e}")
            adb_path = 'adb'
        
        # 创建 DeviceManager 实例
        manager = DeviceManager(adb_path=adb_path)
        
        # 获取当前通过 ADB 连接的设备列表
        try:
            devices_info = manager.list_devices()
            connected_device_ids = [info['device_id'] for info in devices_info]
            logger.info(f"当前 ADB 连接的设备: {connected_device_ids}")
        except Exception as e:
            logger.error(f"ADB 命令执行失败: {str(e)}")
            # 如果 ADB 不可用，将所有非锁定设备标记为离线
            offline_count = AppDevice.objects.exclude(
                status='locked'
            ).update(status='offline')
            logger.info(f"ADB 不可用，将 {offline_count} 个设备标记为离线")
            return {
                'success': False,
                'message': f'ADB 命令执行失败: {str(e)}',
                'offline_count': offline_count
            }
        
        # 更新在线设备的状态
        online_count = 0
        for device_info in devices_info:
            device_id = device_info['device_id']
            try:
                device = AppDevice.objects.get(device_id=device_id)
                # 只有当设备未被锁定时，才更新状态为 available
                if device.status != 'locked':
                    device.status = 'available'
                    device.save(update_fields=['status', 'updated_at'])
                    online_count += 1
                    logger.debug(f"更新设备 {device_id} 状态为 available")
            except AppDevice.DoesNotExist:
                logger.debug(f"设备 {device_id} 不在数据库中，跳过")
        
        # 将不在 ADB 列表中的设备标记为离线（但保持 locked 状态）
        offline_count = AppDevice.objects.exclude(
            device_id__in=connected_device_ids
        ).exclude(
            status='locked'  # 保持锁定设备的状态
        ).update(status='offline')
        
        logger.info(f"设备状态检查完成: {online_count} 个在线, {offline_count} 个离线")
        
        return {
            'success': True,
            'message': f'设备状态检查完成',
            'online_count': online_count,
            'offline_count': offline_count,
            'total_connected': len(connected_device_ids)
        }
        
    except Exception as e:
        logger.error(f"检查设备状态失败: {str(e)}", exc_info=True)
        return {
            'success': False,
            'message': f'检查设备状态失败: {str(e)}'
        }
