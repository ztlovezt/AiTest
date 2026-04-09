# -*- coding: utf-8 -*-
"""
UI 自动化执行引擎
封装 Playwright/Selenium 步骤执行逻辑，供 pytest 测试文件调用
"""
import os
import time
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from django.conf import settings

logger = logging.getLogger(__name__)


class UiFlowRunner:
    """UI 自动化执行引擎，封装 Playwright/Selenium 步骤执行"""

    def __init__(self, engine='playwright', browser='chrome', headless=False):
        self.engine = engine
        self.browser = browser
        self.headless = headless
        self.current_page = None
        self.context = None
        self.screenshots_dir = os.path.join(settings.MEDIA_ROOT, settings.PATHS_UI_AUTOMATION_SCREENSHOTS)
        os.makedirs(self.screenshots_dir, exist_ok=True)

    def run_test_case(self, case_data: Dict[str, Any], base_url: str = '') -> Dict[str, Any]:
        """执行单个测试用例

        Args:
            case_data: 用例数据字典，包含 id, name, steps 等
            base_url: 项目基础URL

        Returns:
            执行结果字典
        """
        if self.engine == 'playwright':
            return self._run_with_playwright(case_data, base_url)
        elif self.engine == 'selenium':
            return self._run_with_selenium(case_data, base_url)
        else:
            return {
                'test_case_id': case_data.get('id'),
                'test_case_name': case_data.get('name', 'Unknown'),
                'status': 'failed',
                'steps': [],
                'error': f'不支持的引擎: {self.engine}',
                'start_time': datetime.now().isoformat(),
                'end_time': datetime.now().isoformat(),
                'screenshots': []
            }

    def _run_with_playwright(self, case_data: Dict[str, Any], base_url: str) -> Dict[str, Any]:
        """使用 Playwright 执行单个测试用例"""
        from playwright.sync_api import sync_playwright
        from .variable_resolver import resolve_variables

        result = {
            'test_case_id': case_data.get('id'),
            'test_case_name': case_data.get('name', 'Unknown'),
            'status': 'passed',
            'steps': [],
            'error': None,
            'start_time': datetime.now().isoformat(),
            'screenshots': []
        }

        with sync_playwright() as p:
            try:
                common_args = [
                    '--disable-blink-features=AutomationControlled',
                    '--ignore-certificate-errors',
                    '--allow-insecure-localhost',
                    '--disable-web-security',
                ]

                if self.browser == 'firefox':
                    browser = p.firefox.launch(headless=self.headless, args=common_args)
                elif self.browser == 'safari':
                    browser = p.webkit.launch(headless=self.headless, args=common_args)
                else:
                    browser = p.chromium.launch(headless=self.headless, args=common_args)

                self.context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
                )
                self.current_page = self.context.new_page()

                if base_url:
                    import platform
                    is_linux = platform.system() == 'Linux'
                    self.current_page.goto(base_url, wait_until='networkidle',
                                           timeout=settings.TIMEOUTS_PAGE_LOAD_NETWORKIDLE)
                    extra_wait = 3 if is_linux else 2
                    time.sleep(extra_wait)

                just_switched_tab = False
                for step_data in case_data.get('steps', []):
                    step_data['_just_switched_tab'] = just_switched_tab
                    just_switched_tab = False

                    step_result = self._execute_step_playwright(step_data, resolve_variables)
                    result['steps'].append(step_result)

                    if step_result.get('switched_page'):
                        self.current_page = step_result['switched_page']
                        del step_result['switched_page']
                        just_switched_tab = True

                    if step_result['success'] and step_data['action_type'] in ['click', 'fill', 'hover']:
                        if step_data['action_type'] == 'click':
                            try:
                                self.current_page.wait_for_timeout(500)
                                self.current_page.wait_for_load_state('domcontentloaded', timeout=8000)
                            except Exception:
                                self.current_page.wait_for_timeout(800)
                        else:
                            self.current_page.wait_for_timeout(300)

                    if not step_result['success']:
                        result['status'] = 'failed'
                        result['error'] = step_result.get('error', f"步骤 {step_data['step_number']} 执行失败")
                        try:
                            import base64
                            screenshot_bytes = self.current_page.screenshot(timeout=settings.TIMEOUTS_SCREENSHOT)
                            screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                            result['screenshots'].append({
                                'url': f'data:image/png;base64,{screenshot_base64}',
                                'description': f'步骤 {step_data["step_number"]} 失败截图: {step_data.get("description", "")}',
                                'step_number': step_data['step_number'],
                                'timestamp': datetime.now().isoformat()
                            })
                        except Exception as screenshot_error:
                            logger.warning(f"捕获失败截图失败: {screenshot_error}")
                        break

                try:
                    self.current_page.wait_for_timeout(1000)
                    self.current_page.wait_for_load_state('domcontentloaded', timeout=10000)
                except Exception:
                    self.current_page.wait_for_timeout(2000)

            except Exception as e:
                result['status'] = 'failed'
                result['error'] = str(e)
                try:
                    if self.current_page:
                        import base64
                        screenshot_bytes = self.current_page.screenshot(timeout=settings.TIMEOUTS_SCREENSHOT)
                        screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                        result['screenshots'].append({
                            'url': f'data:image/png;base64,{screenshot_base64}',
                            'description': f'异常截图: {str(e)}',
                            'step_number': None,
                            'timestamp': datetime.now().isoformat()
                        })
                except Exception:
                    pass
            finally:
                try:
                    browser.close()
                except Exception:
                    pass

        result['end_time'] = datetime.now().isoformat()
        return result

    def _run_with_selenium(self, case_data: Dict[str, Any], base_url: str) -> Dict[str, Any]:
        """使用 Selenium 执行单个测试用例"""
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from .variable_resolver import resolve_variables

        result = {
            'test_case_id': case_data.get('id'),
            'test_case_name': case_data.get('name', 'Unknown'),
            'status': 'passed',
            'steps': [],
            'error': None,
            'start_time': datetime.now().isoformat(),
            'screenshots': []
        }

        driver = None
        try:
            driver = self._create_selenium_driver()

            if base_url:
                driver.get(base_url)
                time.sleep(3)

            for step_data in case_data.get('steps', []):
                step_result = self._execute_step_selenium(driver, step_data, resolve_variables)
                result['steps'].append(step_result)

                if step_result['success'] and step_data['action_type'] in ['click', 'fill', 'hover']:
                    if step_data['action_type'] == 'click':
                        try:
                            time.sleep(0.5)
                            WebDriverWait(driver, 8).until(
                                lambda d: d.execute_script("return document.readyState") == "complete"
                            )
                        except Exception:
                            pass
                        time.sleep(0.8)
                    else:
                        time.sleep(0.3)

                if not step_result['success']:
                    result['status'] = 'failed'
                    result['error'] = step_result.get('error', f"步骤 {step_data['step_number']} 执行失败")
                    try:
                        import base64
                        screenshot_bytes = driver.get_screenshot_as_png()
                        screenshot_base64 = base64.b64encode(screenshot_bytes).decode()
                        result['screenshots'].append({
                            'url': f'data:image/png;base64,{screenshot_base64}',
                            'description': f'步骤 {step_data["step_number"]} 失败截图: {step_data.get("description", "")}',
                            'step_number': step_data['step_number'],
                            'timestamp': datetime.now().isoformat()
                        })
                    except Exception:
                        pass
                    break

        except Exception as e:
            result['status'] = 'failed'
            result['error'] = str(e)
            if driver:
                try:
                    import base64
                    screenshot_bytes = driver.get_screenshot_as_png()
                    screenshot_base64 = base64.b64encode(screenshot_bytes).decode()
                    result['screenshots'].append({
                        'url': f'data:image/png;base64,{screenshot_base64}',
                        'description': f'异常截图: {str(e)}',
                        'step_number': None,
                        'timestamp': datetime.now().isoformat()
                    })
                except Exception:
                    pass
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

        result['end_time'] = datetime.now().isoformat()
        return result

    def _create_selenium_driver(self):
        """创建 Selenium WebDriver"""
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options as ChromeOptions
        from selenium.webdriver.firefox.options import Options as FirefoxOptions
        from selenium.webdriver.edge.options import Options as EdgeOptions

        if self.browser == 'firefox':
            options = FirefoxOptions()
            if self.headless:
                options.add_argument('--headless')
            driver = webdriver.Firefox(options=options)
        elif self.browser == 'edge':
            options = EdgeOptions()
            if self.headless:
                options.add_argument('--headless')
            driver = webdriver.Edge(options=options)
        else:
            options = ChromeOptions()
            if self.headless:
                options.add_argument('--headless')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--ignore-certificate-errors')
            options.add_argument('--disable-web-security')
            driver = webdriver.Chrome(options=options)

        driver.set_page_load_timeout(30)
        driver.implicitly_wait(2)
        return driver

    def _execute_step_playwright(self, step_data: Dict[str, Any], resolve_fn) -> Dict[str, Any]:
        """执行单个 Playwright 步骤（精简版，保留核心逻辑）"""
        import re
        start_time = time.time()

        step_result = {
            'step_number': step_data['step_number'],
            'action_type': step_data['action_type'],
            'description': step_data['description'],
            'success': False,
            'error': None
        }

        try:
            if step_data['action_type'] == 'assert' and step_data.get('assert_type') == 'urlContains':
                resolved_assert_value = resolve_fn(step_data.get('assert_value', ''))
                current_url = self.current_page.url if self.current_page else ''
                if resolved_assert_value in current_url:
                    step_result['success'] = True
                else:
                    step_result['error'] = f"断言失败: 当前URL不包含 '{resolved_assert_value}'\n当前URL: '{current_url}'"
                return step_result

            if step_data['element']:
                element = step_data['element']
                locator_value = element['locator_value']
                locator_strategy = element['locator_strategy'].lower()
                element_name = element.get('name', '未知元素')

                if locator_strategy in ['css', 'css selector']:
                    selector = locator_value
                elif locator_strategy == 'xpath':
                    selector = f'xpath={locator_value}'
                elif locator_strategy == 'id':
                    selector = f'#{locator_value}'
                elif locator_strategy == 'name':
                    selector = f'[name="{locator_value}"]'
                elif locator_strategy == 'text':
                    selector = f'text={locator_value}'
                else:
                    selector = locator_value

                if step_data['action_type'] == 'click':
                    if step_data.get('_just_switched_tab'):
                        self.current_page.bring_to_front()
                        try:
                            self.current_page.locator(selector).scroll_into_view_if_needed(timeout=settings.TIMEOUTS_ELEMENT_SCROLL)
                        except Exception:
                            pass
                        extended_timeout = max(step_data['wait_time'], 10000)
                        self.current_page.click(selector, timeout=extended_timeout)
                    else:
                        self.current_page.click(selector, timeout=step_data['wait_time'])
                    step_result['success'] = True

                elif step_data['action_type'] == 'fill':
                    resolved_value = resolve_fn(step_data['input_value'])
                    if step_data.get('_just_switched_tab'):
                        self.current_page.bring_to_front()
                        extended_timeout = max(step_data['wait_time'], 10000)
                        self.current_page.fill(selector, resolved_value, timeout=extended_timeout)
                    else:
                        self.current_page.fill(selector, resolved_value, timeout=step_data['wait_time'])
                    step_result['success'] = True

                elif step_data['action_type'] == 'getText':
                    text = self.current_page.text_content(selector, timeout=step_data['wait_time'])
                    step_result['result'] = text
                    step_result['success'] = True

                elif step_data['action_type'] == 'waitFor':
                    is_dropdown = (
                        (locator_strategy == 'xpath' and '//li' in locator_value) or
                        'el-select-dropdown' in locator_value.lower() or
                        'role="option"' in locator_value.lower()
                    )
                    if is_dropdown:
                        self.current_page.wait_for_selector(selector, state='attached', timeout=step_data['wait_time'])
                    else:
                        self.current_page.wait_for_selector(selector, timeout=step_data['wait_time'])
                    step_result['success'] = True

                elif step_data['action_type'] == 'hover':
                    self.current_page.hover(selector, timeout=step_data['wait_time'])
                    step_result['success'] = True

                elif step_data['action_type'] == 'scroll':
                    self.current_page.locator(selector).scroll_into_view_if_needed()
                    step_result['success'] = True

                elif step_data['action_type'] == 'screenshot':
                    screenshot_path = os.path.join(self.screenshots_dir, f'step_{step_data["step_number"]}.png')
                    self.current_page.screenshot(path=screenshot_path)
                    step_result['screenshot'] = screenshot_path
                    step_result['success'] = True

                elif step_data['action_type'] == 'assert':
                    resolved_assert_value = resolve_fn(step_data['assert_value'])
                    if step_data['assert_type'] == 'textContains':
                        text = self.current_page.text_content(selector, timeout=step_data['wait_time'])
                        if resolved_assert_value in text:
                            step_result['success'] = True
                        else:
                            step_result['error'] = f"断言失败: 文本不包含 '{resolved_assert_value}'\n实际文本: '{text}'"
                    elif step_data['assert_type'] == 'textEquals':
                        text = self.current_page.text_content(selector, timeout=step_data['wait_time'])
                        if text == resolved_assert_value:
                            step_result['success'] = True
                        else:
                            step_result['error'] = f"断言失败: 文本不等于 '{resolved_assert_value}'\n期望: '{resolved_assert_value}'\n实际: '{text}'"
                    elif step_data['assert_type'] == 'isVisible':
                        is_visible = self.current_page.is_visible(selector)
                        step_result['success'] = is_visible
                        if not is_visible:
                            step_result['error'] = f"断言失败: 元素 '{element_name}' 不可见"
                    elif step_data['assert_type'] == 'exists':
                        count = self.current_page.locator(selector).count()
                        step_result['success'] = count > 0
                        if count == 0:
                            step_result['error'] = f"断言失败: 元素 '{element_name}' 不存在"
                    elif step_data['assert_type'] == 'hasAttribute':
                        attr_name = resolved_assert_value
                        attr_value = step_data.get('input_value', '')
                        actual = self.current_page.get_attribute(selector, attr_name)
                        if actual and attr_value in actual:
                            step_result['success'] = True
                        else:
                            step_result['error'] = f"断言失败: 属性 '{attr_name}' 值不包含 '{attr_value}'\n实际: '{actual}'"

                elif step_data['action_type'] == 'switchTab':
                    user_wait = step_data.get('wait_time', 0) or 0
                    timeout = max(user_wait / 1000, 5.0)
                    start_wait = time.time()
                    current_page = self.current_page

                    while True:
                        pages = self.current_page.context.pages
                        candidates = [pg for pg in pages if pg != current_page]
                        should_switch = False

                        if step_data['input_value'] and str(step_data['input_value']).isdigit():
                            idx = int(step_data['input_value'])
                            if 0 <= idx < len(pages):
                                should_switch = True
                        else:
                            if candidates or len(pages) > 1:
                                should_switch = True

                        if should_switch:
                            break
                        if time.time() - start_wait > timeout:
                            break
                        self.current_page.wait_for_timeout(500)

                    pages = self.current_page.context.pages
                    if step_data['input_value'] and str(step_data['input_value']).isdigit():
                        idx = int(step_data['input_value'])
                        target_page = pages[idx]
                    else:
                        candidates = [pg for pg in pages if pg != current_page]
                        target_page = candidates[-1] if candidates else (pages[-1] if len(pages) > 1 else None)

                    if target_page:
                        target_page.bring_to_front()
                        try:
                            target_page.wait_for_load_state('networkidle', timeout=settings.TIMEOUTS_PAGE_LOAD_NETWORKIDLE)
                        except Exception:
                            try:
                                target_page.wait_for_load_state('domcontentloaded', timeout=settings.TIMEOUTS_PAGE_LOAD_DOMCONTENTLOADED)
                            except Exception:
                                pass
                        target_page.wait_for_timeout(1500)
                        self.current_page = target_page
                        step_result['switched_page'] = target_page
                        step_result['success'] = True
                    else:
                        step_result['error'] = f"切换标签页失败: 在 {timeout} 秒内未检测到新标签页"

                elif step_data['action_type'] == 'navigateTo':
                    target_url = step_data.get('input_value', '')
                    if not target_url:
                        step_result['error'] = '跳转失败: 未提供URL地址'
                    else:
                        self.current_page.goto(target_url, timeout=15000)
                        try:
                            self.current_page.wait_for_load_state('networkidle', timeout=15000)
                        except Exception:
                            try:
                                self.current_page.wait_for_load_state('domcontentloaded', timeout=15000)
                            except Exception:
                                pass
                        step_result['success'] = True
                else:
                    step_result['error'] = f'未知的操作类型: {step_data["action_type"]}'
            else:
                if step_data['action_type'] == 'wait':
                    self.current_page.wait_for_timeout(step_data['wait_time'])
                    step_result['success'] = True
                elif step_data['action_type'] == 'navigateTo':
                    target_url = step_data.get('input_value', '')
                    if not target_url:
                        step_result['error'] = '跳转失败: 未提供URL地址'
                    else:
                        self.current_page.goto(target_url, timeout=15000)
                        try:
                            self.current_page.wait_for_load_state('networkidle', timeout=15000)
                        except Exception:
                            try:
                                self.current_page.wait_for_load_state('domcontentloaded', timeout=15000)
                            except Exception:
                                pass
                        step_result['success'] = True
                elif step_data['action_type'] == 'switchTab':
                    user_wait = step_data.get('wait_time', 0) or 0
                    timeout = max(user_wait / 1000, 5.0)
                    start_wait = time.time()
                    current_page = self.current_page

                    while True:
                        pages = self.current_page.context.pages
                        candidates = [pg for pg in pages if pg != current_page]
                        if candidates or len(pages) > 1:
                            break
                        if time.time() - start_wait > timeout:
                            break
                        self.current_page.wait_for_timeout(500)

                    pages = self.current_page.context.pages
                    candidates = [pg for pg in pages if pg != current_page]
                    if candidates:
                        target_page = candidates[-1]
                        target_page.bring_to_front()
                        try:
                            target_page.wait_for_load_state('networkidle', timeout=settings.TIMEOUTS_PAGE_LOAD_NETWORKIDLE)
                        except Exception:
                            pass
                        target_page.wait_for_timeout(1500)
                        self.current_page = target_page
                        step_result['switched_page'] = target_page
                        step_result['success'] = True
                    else:
                        step_result['error'] = f"切换标签页失败: 在 {timeout} 秒内未检测到新标签页"
                else:
                    step_result['error'] = f'未知的操作类型(无元素): {step_data["action_type"]}'

        except Exception as e:
            error_str = str(e)
            error_type = type(e).__name__
            if error_type not in error_str and error_type != 'Exception':
                error_str = f"{error_type}: {error_str}"

            element_name = step_data.get('element', {}).get('name', '未知') if step_data.get('element') else '页面'
            locator_info = f"{step_data['element']['locator_strategy']}={step_data['element']['locator_value']}" if step_data.get('element') else '无'
            execution_time = round(time.time() - start_time, 2)

            step_result['error'] = f"执行失败\n  - 元素: '{element_name}'\n  - 定位器: {locator_info}\n  - 执行时间: {execution_time}秒\n  - 错误: {error_str}"

        return step_result

    def _execute_step_selenium(self, driver, step_data: Dict[str, Any], resolve_fn) -> Dict[str, Any]:
        """执行单个 Selenium 步骤"""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException, NoSuchElementException

        step_result = {
            'step_number': step_data['step_number'],
            'action_type': step_data['action_type'],
            'description': step_data['description'],
            'success': False,
            'error': None
        }

        try:
            if step_data['action_type'] == 'assert' and step_data.get('assert_type') == 'urlContains':
                resolved_assert_value = resolve_fn(step_data.get('assert_value', ''))
                current_url = driver.current_url
                if resolved_assert_value in current_url:
                    step_result['success'] = True
                else:
                    step_result['error'] = f"断言失败: 当前URL不包含 '{resolved_assert_value}'\n当前URL: '{current_url}'"
                return step_result

            if step_data['element']:
                element = step_data['element']
                locator_value = element['locator_value']
                locator_strategy = element['locator_strategy'].lower()
                element_name = element.get('name', '未知元素')

                by_map = {
                    'css': By.CSS_SELECTOR,
                    'css selector': By.CSS_SELECTOR,
                    'xpath': By.XPATH,
                    'id': By.ID,
                    'name': By.NAME,
                    'class': By.CLASS_NAME,
                    'class name': By.CLASS_NAME,
                    'tag': By.TAG_NAME,
                    'tag name': By.TAG_NAME,
                    'link text': By.LINK_TEXT,
                    'partial link text': By.PARTIAL_LINK_TEXT,
                }
                by = by_map.get(locator_strategy, By.CSS_SELECTOR)

                if step_data['action_type'] == 'click':
                    wait = WebDriverWait(driver, step_data['wait_time'] / 1000)
                    elem = wait.until(EC.element_to_be_clickable((by, locator_value)))
                    elem.click()
                    step_result['success'] = True

                elif step_data['action_type'] == 'fill':
                    resolved_value = resolve_fn(step_data['input_value'])
                    wait = WebDriverWait(driver, step_data['wait_time'] / 1000)
                    elem = wait.until(EC.presence_of_element_located((by, locator_value)))
                    elem.clear()
                    elem.send_keys(resolved_value)
                    step_result['success'] = True

                elif step_data['action_type'] == 'getText':
                    wait = WebDriverWait(driver, step_data['wait_time'] / 1000)
                    elem = wait.until(EC.presence_of_element_located((by, locator_value)))
                    step_result['result'] = elem.text
                    step_result['success'] = True

                elif step_data['action_type'] == 'waitFor':
                    wait = WebDriverWait(driver, step_data['wait_time'] / 1000)
                    wait.until(EC.presence_of_element_located((by, locator_value)))
                    step_result['success'] = True

                elif step_data['action_type'] == 'hover':
                    from selenium.webdriver.common.action_chains import ActionChains
                    wait = WebDriverWait(driver, step_data['wait_time'] / 1000)
                    elem = wait.until(EC.presence_of_element_located((by, locator_value)))
                    ActionChains(driver).move_to_element(elem).perform()
                    step_result['success'] = True

                elif step_data['action_type'] == 'screenshot':
                    screenshot_path = os.path.join(self.screenshots_dir, f'step_{step_data["step_number"]}.png')
                    driver.save_screenshot(screenshot_path)
                    step_result['screenshot'] = screenshot_path
                    step_result['success'] = True

                elif step_data['action_type'] == 'assert':
                    resolved_assert_value = resolve_fn(step_data['assert_value'])
                    wait = WebDriverWait(driver, step_data['wait_time'] / 1000)
                    elem = wait.until(EC.presence_of_element_located((by, locator_value)))

                    if step_data['assert_type'] == 'textContains':
                        if resolved_assert_value in elem.text:
                            step_result['success'] = True
                        else:
                            step_result['error'] = f"断言失败: 文本不包含 '{resolved_assert_value}'\n实际文本: '{elem.text}'"
                    elif step_data['assert_type'] == 'textEquals':
                        if elem.text == resolved_assert_value:
                            step_result['success'] = True
                        else:
                            step_result['error'] = f"断言失败: 文本不等于 '{resolved_assert_value}'\n实际: '{elem.text}'"
                    elif step_data['assert_type'] == 'isVisible':
                        step_result['success'] = elem.is_displayed()
                        if not step_result['success']:
                            step_result['error'] = f"断言失败: 元素 '{element_name}' 不可见"
                    elif step_data['assert_type'] == 'exists':
                        step_result['success'] = True
                    elif step_data['assert_type'] == 'hasAttribute':
                        attr_name = resolved_assert_value
                        attr_value = step_data.get('input_value', '')
                        actual = elem.get_attribute(attr_name)
                        if actual and attr_value in actual:
                            step_result['success'] = True
                        else:
                            step_result['error'] = f"断言失败: 属性 '{attr_name}' 值不包含 '{attr_value}'\n实际: '{actual}'"

                elif step_data['action_type'] == 'navigateTo':
                    target_url = step_data.get('input_value', '')
                    if not target_url:
                        step_result['error'] = '跳转失败: 未提供URL地址'
                    else:
                        driver.get(target_url)
                        step_result['success'] = True
                else:
                    step_result['error'] = f'未知的操作类型: {step_data["action_type"]}'
            else:
                if step_data['action_type'] == 'wait':
                    time.sleep(step_data['wait_time'] / 1000)
                    step_result['success'] = True
                elif step_data['action_type'] == 'navigateTo':
                    target_url = step_data.get('input_value', '')
                    if not target_url:
                        step_result['error'] = '跳转失败: 未提供URL地址'
                    else:
                        driver.get(target_url)
                        step_result['success'] = True
                else:
                    step_result['error'] = f'未知的操作类型(无元素): {step_data["action_type"]}'

        except Exception as e:
            error_str = str(e)
            error_type = type(e).__name__
            if error_type not in error_str:
                error_str = f"{error_type}: {error_str}"
            step_result['error'] = error_str

        return step_result
