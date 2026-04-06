# -*- coding: utf-8 -*-
# -----------------------------
# @Author    : 影子
# @Time      : 2026/4/31 10:27
# @Software  : PyCharm
# @FileName  : base_executor.py
# -----------------------------
"""
统一的基础测试执行器 - 提取 API/UI/APP 执行器的公共逻辑
保证三个执行器的执行方式和报告生成保持一致

关键统一点：
1. 执行记录管理：统一的 _create_execution_record 和 _update_execution_result 方法
2. Allure 命令查找：统一的 _find_allure_command 方法
3. Allure 报告生成：统一的 _generate_allure_report 方法（含单文件报告）
4. Allure 结果解析：统一的 _parse_allure_results 方法
5. 环境信息写入：统一的 _write_allure_environment 和 _write_allure_executor 方法
6. Java 环境检查：统一的 _check_java_environment 方法
7. pytest 执行封装：统一的 _execute_with_pytest 方法
8. 日志收集：统一的 _collect_logs 方法
"""
import os
import sys
import json
import shutil
import subprocess
import glob
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from django.conf import settings
from django.utils import timezone
from loguru import logger


class BaseTestExecutor:
    """基础测试执行器 - 提取公共的 Allure 报告生成和解析逻辑"""

    MODULE_NAME = None

    ALLURE_RESULTS_DIR = 'allure-results'
    ALLURE_REPORTS_DIR = 'allure-reports'
    ALLURE_SINGLE_FILE_DIR = 'allure-single-file'

    def __init__(self, base_path: Optional[str] = None):
        """
        初始化基础执行器
        :param base_path: 项目基础路径，默认使用 Django BASE_DIR
        """
        if base_path is None:
            self.base_path = settings.BASE_DIR
        else:
            self.base_path = base_path

        if not os.path.exists(self.base_path):
            raise ValueError(f"测试项目路径不存在: {self.base_path}")

        self.execution = None
        self._current_process: Optional[subprocess.Popen] = None

    # ======================== 执行记录管理 ========================

    def _create_execution_record(self, model_class, **kwargs):
        """
        创建执行记录（统一入口）
        :param model_class: 执行记录模型类
        :param **kwargs: 模型字段参数
        :return: 创建的执行记录实例
        """
        self.execution = model_class.objects.create(
            status='RUNNING',
            started_at=timezone.now(),
            **kwargs
        )
        return self.execution

    def _update_execution_result(self, status: str, **kwargs):
        """
        更新执行结果
        :param status: 执行状态
        :param **kwargs: 其他要更新的字段
        :return:
        """
        if not self.execution:
            return

        self.execution.status = status
        self.execution.finished_at = timezone.now()

        for key, value in kwargs.items():
            if hasattr(self.execution, key):
                setattr(self.execution, key, value)

        self.execution.save()

    # ======================== 目录管理 ========================

    def _get_allure_results_dir(self, execution_id: Optional[int] = None) -> str:
        """
        获取 Allure 结果目录
        :param execution_id: 执行记录ID
        :return: Allure 结果目录路径
        """
        raise NotImplementedError("子类必须实现 _get_allure_results_dir 方法")

    def _get_allure_report_dir(self, execution_id: Optional[int] = None) -> str:
        """
        获取 Allure 报告目录
        :param execution_id: 执行记录ID
        :return: Allure 报告目录路径
        """
        raise NotImplementedError("子类必须实现 _get_allure_report_dir 方法")

    def _get_allure_single_file_dir(self, execution_id: Optional[int] = None) -> str:
        """
        获取 Allure single-file 报告目录
        :param execution_id: 执行记录ID
        :return: Allure single-file 报告目录路径
        """
        raise NotImplementedError("子类必须实现 _get_allure_single_file_dir 方法")

    def _get_report_url(self, execution_id: int) -> str:
        """
        获取报告访问URL
        :param execution_id: 执行记录ID
        :return: 报告访问URL
        """
        raise NotImplementedError("子类必须实现 _get_report_url 方法")

    def _get_log_file_path(self, username: str) -> str:
        """
        生成日志文件路径
        :param username: 用户名
        :return: 日志文件路径
        """
        today = datetime.now().strftime('%Y-%m-%d')
        log_dir = os.path.join(
            str(self.base_path), 'logs',
            self.MODULE_NAME.lower() if self.MODULE_NAME else 'test',
            username
        )
        os.makedirs(log_dir, exist_ok=True)
        return os.path.join(log_dir, f'{today}.log')

    def _prepare_allure_directory(self, results_dir: str):
        """
        准备 Allure 结果目录（清空旧文件）
        :param results_dir: Allure 结果目录路径
        :return:
        """
        if os.path.exists(results_dir):
            shutil.rmtree(results_dir)
        os.makedirs(results_dir, exist_ok=True)

    # ======================== pytest 执行封装 ========================

    def _build_pythonpath(self) -> str:
        """
        构建 PYTHONPATH 环境变量
        关键说明:
        - DJANGO_SETTINGS_MODULE = 'backend.settings'
        - Python 需要从 backend 目录开始查找 backend 包
        - 绝对不能包含项目根目录（backend 的父目录），
          否则 Python 会优先从项目根目录查找 backend 模块，
          导致找不到 backend.settings
        :return: PYTHONPATH 字符串
        """
        python_path_parts = [
            str(self.base_path),
            os.path.join(str(self.base_path), 'apps'),
        ]

        _project_root = str(Path(self.base_path).parent)
        for p in sys.path:
            if p and os.path.exists(str(p)) and str(p) not in python_path_parts:
                p_str = str(p)
                if p_str == _project_root:
                    continue
                if p_str == str(self.base_path):
                    continue
                if 'site-packages' in p_str or not p_str.endswith('.exe'):
                    python_path_parts.append(p_str)

        return os.pathsep.join(python_path_parts)

    def _build_env_variables(self, extra_vars: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        构建 pytest 执行环境变量
        :param extra_vars: 额外的环境变量
        :return: 环境变量字典
        """
        env = os.environ.copy()
        env['PYTHONPATH'] = self._build_pythonpath()
        env['DJANGO_SETTINGS_MODULE'] = 'backend.settings'
        env['PYTHONUTF8'] = '1'
        env['PYTHONIOENCODING'] = 'utf-8'

        if extra_vars:
            for key, value in extra_vars.items():
                env[key] = str(value)

        return env

    def _execute_with_pytest(
            self,
            test_dir: str,
            env_vars: Dict[str, str],
            execution_id: int,
            extra_args: Optional[List[str]] = None
    ) -> tuple:
        """
        统一的 pytest 执行方法
        :param test_dir: 测试目录
        :param env_vars: 环境变量字典
        :param execution_id: 执行记录ID
        :param extra_args: 额外的 pytest 参数
        :return: (exit_code, results_dir) 元组
        """
        results_dir = self._get_allure_results_dir(execution_id)
        self._prepare_allure_directory(results_dir)

        env_info = self._get_env_info()
        self._write_allure_environment(results_dir, env_info)

        executor_info = self._get_executor_info(execution_id)
        self._write_allure_executor(results_dir, executor_info)

        env = self._build_env_variables(env_vars)

        pytest_args = [
            sys.executable, '-m', 'pytest',
            test_dir, '-s', '-v',
            '--alluredir', results_dir,
            '--tb=short',
        ]

        if extra_args:
            pytest_args.extend(extra_args)

        logger.info(f"执行 pytest 命令: {' '.join(pytest_args)}")
        logger.info(f"工作目录: {self.base_path}")

        process = subprocess.Popen(
            pytest_args,
            cwd=self.base_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='ignore',
            bufsize=1,
            env=env
        )
        self._current_process = process

        username = env_vars.get('USERNAME', env_vars.get('UI_USERNAME', env_vars.get('APP_USERNAME', 'unknown')))
        self._collect_logs(process, execution_id, username)

        exit_code = process.wait()
        self._current_process = None

        logger.info(f"pytest 执行完成，退出码: {exit_code}")

        return exit_code, results_dir

    def _collect_logs(self, process: subprocess.Popen, execution_id: int, username: str):
        """
        收集 pytest 执行日志
        :param process: pytest 子进程
        :param execution_id: 执行记录ID
        :param username: 用户名
        :return:
        """
        log_file_path = self._get_log_file_path(username)
        output_lines = []
        important_patterns = ['PASSED', 'FAILED', 'ERROR', 'SKIPPED', 'collected', 'passed', 'failed']

        with open(log_file_path, 'a', encoding='utf-8') as log_file:
            log_file.write(f"\n{'=' * 80}\n")
            log_file.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                           f"执行记录 ID: {execution_id}\n")
            log_file.write(f"{'=' * 80}\n")

            if process.stdout:
                for line in process.stdout:
                    line = line.rstrip()
                    if line:
                        output_lines.append(line)
                        log_file.write(line + '\n')
                        if any(pattern in line for pattern in important_patterns):
                            logger.info(f"[pytest] {line}")

            log_file.write(f"\n[执行完毕]\n")

        logger.info(f"执行日志已保存: {log_file_path}")

    def stop(self):
        """停止当前执行的测试"""
        if self._current_process:
            try:
                self._current_process.terminate()
                self._current_process.wait(timeout=getattr(settings, 'TIMEOUTS_PROCESS_WAIT', 10))
                logger.info("测试执行已停止")
            except subprocess.TimeoutExpired:
                self._current_process.kill()
                logger.warning("测试执行被强制终止")
            except Exception as e:
                logger.error(f"停止测试失败: {str(e)}")
            finally:
                self._current_process = None

    # ======================== Allure 报告生成（公开方法） ========================

    def generate_report(self, execution_id: int) -> bool:
        """
        生成 Allure 报告（公开方法）
        :param execution_id: 执行记录ID
        :return: 生成成功返回 True，失败返回 False
        """
        results_dir = self._get_allure_results_dir(execution_id)
        report_dir = self._get_allure_report_dir(execution_id)
        single_file_dir = self._get_allure_single_file_dir(execution_id)
        timeout = getattr(settings, 'TIMEOUTS_ALLURE_REPORT', 30)

        success = self._generate_allure_report(
            results_dir=results_dir,
            report_dir=report_dir,
            single_file_dir=single_file_dir,
            timeout=timeout
        )

        if success and self.execution:
            self.execution.report_url = self._get_report_url(execution_id)
            self.execution.report_status = 'SUCCESS'
            self.execution.save(update_fields=['report_url', 'report_status'])

        return success

    # ======================== Allure 结果文件生成（用于非pytest执行） ========================

    def _generate_allure_result_file(
            self,
            results_dir: str,
            name: str,
            status: str,
            start_time: float,
            duration: float,
            description: str = '',
            error_message: str = '',
            labels: Optional[List[Dict]] = None,
            parameters: Optional[List[Dict]] = None
    ) -> str:
        """
        生成单个 Allure 结果文件
        :param results_dir: 结果目录
        :param name: 测试名称
        :param status: 测试状态 (passed/failed/broken)
        :param start_time: 开始时间戳（秒）
        :param duration: 持续时间（秒）
        :param description: 描述
        :param error_message: 错误信息
        :param labels: 标签列表
        :param parameters: 参数列表
        :return: 生成的文件UUID
        """
        test_uuid = str(uuid.uuid4())
        start_ms = int(start_time * 1000)
        stop_ms = int((start_time + duration) * 1000)

        test_result = {
            "uuid": test_uuid,
            "name": name,
            "fullName": name,
            "historyId": f"{name}-{start_time}",
            "start": start_ms,
            "stop": stop_ms,
            "labels": labels or [],
            "parameters": parameters or [],
        }

        if status == 'passed':
            test_result["status"] = "passed"
            test_result["statusDetails"] = {"known": False, "muted": False, "flaky": False}
        else:
            test_result["status"] = "failed"
            test_result["statusDetails"] = {
                "known": False,
                "muted": False,
                "flaky": False,
                "message": error_message or 'Assertion failed',
                "trace": error_message or ''
            }

        result_file = os.path.join(results_dir, f"{test_uuid}-result.json")
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(test_result, f, ensure_ascii=False, indent=2)

        return test_uuid

    # ======================== Allure 命令查找 ========================

    def _find_allure_command(self) -> Optional[str]:
        """
        查找项目内置的 Allure 命令（跨平台）
        :return: Allure 命令的完整路径，找不到时返回 None
        """
        import platform

        project_root = Path(settings.BASE_DIR).parent
        allure_bin_path = settings.ALLURE_BIN_PATH

        if platform.system() == 'Windows':
            allure_executable = 'allure.bat'
        else:
            allure_executable = 'allure'

        if os.path.isabs(allure_bin_path):
            builtin_allure = Path(allure_bin_path) / allure_executable
        else:
            builtin_allure = project_root / allure_bin_path / allure_executable

        if builtin_allure.exists():
            return str(builtin_allure)

        possible_paths = [
            project_root / 'expand' / 'allure' / 'bin' / allure_executable,
            Path('/usr/local/bin/allure'),
            Path('/usr/bin/allure'),
        ]
        for path in possible_paths:
            if path.exists():
                return str(path)

        logger.warning(f"未找到 Allure 命令: {builtin_allure}")
        return None

    # ======================== Allure 结果解析 ========================

    def _parse_allure_results(self, results_dir: str) -> Dict[str, Any]:
        """
        解析 Allure result JSON 文件，提取测试结果
        :param results_dir: Allure 结果目录
        :return: 包含 passed, failed, skipped, test_results 的字典
        """
        test_results = []
        passed = 0
        failed = 0
        skipped = 0

        if not os.path.isdir(results_dir):
            return {'test_results': test_results, 'passed': passed, 'failed': failed, 'skipped': skipped}

        for json_file in glob.glob(os.path.join(results_dir, '*-result.json')):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                status = data.get('status', 'unknown')
                name = data.get('name', 'Unknown')
                start_ms = data.get('start', 0)
                stop_ms = data.get('stop', 0)
                duration = (stop_ms - start_ms) / 1000 if stop_ms > start_ms else 0

                error_message = ''
                status_details = data.get('statusDetails', {})
                if status_details:
                    error_message = status_details.get('message', '') or status_details.get('trace', '')

                if status == 'passed':
                    passed += 1
                elif status in ('failed', 'broken'):
                    failed += 1
                else:
                    skipped += 1

                # 从 Allure labels 和 parameters 中提取 method、url、status_code、response_time
                method = ''
                url = ''
                status_code = ''
                response_time = 0

                for label in data.get('labels', []):
                    if label.get('name') == 'method':
                        method = label.get('value', '')
                        break

                for param in data.get('parameters', []):
                    pname = param.get('name', '')
                    pvalue = param.get('value', '')
                    if pname == 'url':
                        url = str(pvalue).strip("'\"")
                    elif pname == 'status_code':
                        status_code = str(pvalue).strip("'\"")
                    elif pname == 'response_time':
                        try:
                            response_time = float(str(pvalue).strip("'\""))
                        except (ValueError, TypeError):
                            pass

                test_results.append({
                    'name': name,
                    'status': status,
                    'duration': duration,
                    'response_time': response_time,
                    'error_message': error_message,
                    'method': method,
                    'url': url,
                    'status_code': status_code,
                    'steps': self._extract_allure_steps(data),
                })
            except Exception as e:
                logger.warning(f"解析 Allure result 文件失败: {json_file}, 错误: {e}")

        return {'test_results': test_results, 'passed': passed, 'failed': failed, 'skipped': skipped}

    def _extract_allure_steps(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        从 Allure 结果数据中提取步骤信息
        :param data: Allure result JSON 数据
        :return: 步骤列表
        """
        steps = []
        test_stage = data.get('testStage', {})
        if not test_stage:
            return steps

        raw_steps = test_stage.get('steps', [])
        for idx, step in enumerate(raw_steps, 1):
            step_status = step.get('status', 'unknown')
            steps.append({
                'step_number': idx,
                'action_type': step.get('name', '').split(']')[0].replace('[', '') if '[' in step.get('name',
                                                                                                      '') else step.get(
                    'name', ''),
                'description': step.get('name', ''),
                'success': step_status == 'passed',
                'error': step.get('statusDetails', {}).get('message', ''),
            })

        return steps

    # ======================== Allure 环境信息写入 ========================

    def _write_allure_environment(self, results_dir: str, env_data: Dict[str, str]):
        """
        写入 Allure 环境信息文件 (environment.xml)
        使用 Allure1 兼容的 XML 格式，每个 <parameter> 必须包含 <name>/<key>/<value> 三个子元素。
        Allure1EnvironmentPlugin 用 <key> 作为 groupingBy 的分组键。
        :param results_dir: Allure 结果目录
        :param env_data: 环境信息字典 (key -> value)
        :return:
        """
        try:
            import xml.etree.ElementTree as ET

            env_file = os.path.join(results_dir, 'environment.xml')
            ns = 'urn:model.commons.qatools.yandex.ru'
            root = ET.Element('environment')
            root.set('xmlns', ns)

            for key, value in env_data.items():
                param = ET.SubElement(root, 'parameter')
                name_elem = ET.SubElement(param, 'name')
                name_elem.text = key
                key_elem = ET.SubElement(param, 'key')
                key_elem.text = key
                val_elem = ET.SubElement(param, 'value')
                val_elem.text = str(value)

            tree = ET.ElementTree(root)
            ET.indent(tree, space='  ')
            tree.write(env_file, encoding='unicode', xml_declaration=True)
            logger.info(f"已写入 Allure 环境信息: {env_file}")
        except Exception as e:
            logger.warning(f"写入 Allure 环境信息失败: {e}")

    def _write_allure_executor(self, results_dir: str, executor_data: Dict[str, Any]):
        """
        写入 Allure 执行器信息文件 (executor.json)
        :param results_dir: Allure 结果目录
        :param executor_data: 执行器信息字典，包含 name, type, buildName, reportUrl, attributes 等
        :return:
        """
        try:
            executor_file = os.path.join(results_dir, 'executor.json')
            with open(executor_file, 'w', encoding='utf-8') as f:
                json.dump(executor_data, f, ensure_ascii=False, indent=2)
            logger.info(f"已写入 Allure 执行器信息: {executor_file}")
        except Exception as e:
            logger.warning(f"写入 Allure 执行器信息失败: {e}")

    # ======================== Java 环境检查 ========================

    def _check_java_environment(self) -> bool:
        """
        检查 Java 运行环境是否可用
        :return: Java 可用返回 True，否则返回 False
        """
        try:
            result = subprocess.run(['java', '-version'], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    # ======================== Allure 报告生成 ========================

    def _generate_allure_report(
            self,
            results_dir: str,
            report_dir: str,
            single_file_dir: Optional[str] = None,
            timeout: int = 30
    ) -> bool:
        """
        生成 Allure 报告（常规 + single-file 离线报告）
        :param results_dir: Allure 原始结果目录
        :param report_dir: 常规报告输出目录
        :param single_file_dir: single-file 报告输出目录（可选）
        :param timeout: 生成报告的超时时间（秒）
        :return: 生成成功返回 True，失败返回 False
        """
        try:
            allure_path = self._find_allure_command()
            if not allure_path:
                logger.warning("未找到 Allure 命令，跳过报告生成")
                return False

            java_available = self._check_java_environment()
            if not java_available:
                logger.warning("Java 环境不可用，跳过报告生成")
                return False

            if not os.path.isdir(results_dir) or not os.listdir(results_dir):
                logger.warning(f"Allure 结果目录为空: {results_dir}")
                return False

            os.makedirs(report_dir, exist_ok=True)

            if os.name == 'nt':
                cmd = ['cmd', '/c', allure_path, 'generate', results_dir, '-o', report_dir, '--clean']
            else:
                cmd = [allure_path, 'generate', results_dir, '-o', report_dir, '--clean']

            logger.info(f"生成 Allure 报告: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

            if result.returncode != 0:
                logger.error(f"Allure 报告生成失败: {result.stderr}")
                return False

            logger.info(f"Allure 报告生成成功: {report_dir}")

            if single_file_dir:
                os.makedirs(single_file_dir, exist_ok=True)

                if os.name == 'nt':
                    sf_cmd = ['cmd', '/c', allure_path, 'generate', results_dir, '-o', single_file_dir, '--clean',
                              '--single-file']
                else:
                    sf_cmd = [allure_path, 'generate', results_dir, '-o', single_file_dir, '--clean', '--single-file']

                logger.info(f"生成 Allure single-file 报告: {' '.join(sf_cmd)}")
                sf_result = subprocess.run(sf_cmd, capture_output=True, text=True, timeout=timeout)

                if sf_result.returncode == 0:
                    logger.info(f"Allure single-file 报告生成成功: {single_file_dir}")
                else:
                    logger.warning(f"Allure single-file 报告生成失败: {sf_result.stderr}")

            return True

        except subprocess.TimeoutExpired:
            logger.error("Allure 报告生成超时")
            return False
        except Exception as e:
            logger.error(f"生成 Allure 报告失败: {str(e)}", exc_info=True)
            return False

    # ======================== 抽象方法（子类实现） ========================

    def _get_env_info(self) -> Dict[str, str]:
        """
        获取环境信息（子类重写）
        :return: 环境信息字典
        """
        return {'Module': self.MODULE_NAME or 'Unknown'}

    def _get_executor_info(self, execution_id: int) -> Dict[str, Any]:
        """
        获取执行器信息（子类重写）
        :param execution_id: 执行记录ID
        :return: 执行器信息字典
        """
        return {
            'name': 'TestHub',
            'type': 'TestHub',
            'buildName': f'{self.MODULE_NAME or "Test"} Execution',
            'reportUrl': self._get_report_url(execution_id) if execution_id else '',
        }

