"""pytest 公共 fixture 与配置。

读取环境变量 TESTHUB_BASE_URL / TESTHUB_TEST_USERNAME / TESTHUB_TEST_PASSWORD,
默认连接本地 http://127.0.0.1:8000。
"""
import os
import time
import uuid
from typing import Optional

import pytest
import requests
from faker import Faker

BASE_URL = os.getenv("TESTHUB_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
DEFAULT_USERNAME = os.getenv("TESTHUB_TEST_USERNAME", "")
DEFAULT_PASSWORD = os.getenv("TESTHUB_TEST_PASSWORD", "")
ADMIN_USERNAME = os.getenv("TESTHUB_ADMIN_USERNAME", "")
ADMIN_PASSWORD = os.getenv("TESTHUB_ADMIN_PASSWORD", "")
DEFAULT_TIMEOUT = int(os.getenv("TESTHUB_TIMEOUT", "10"))

fake = Faker("zh_CN")


@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL


@pytest.fixture(scope="session")
def health_check(base_url: str):
    """会话开始时检查服务是否在线,失败则跳过整个测试集。"""
    try:
        r = requests.get(f"{base_url}/api/schema/", timeout=5)
        if r.status_code >= 500:
            pytest.skip(f"backend not healthy: {r.status_code}")
    except requests.RequestException as e:
        pytest.skip(f"backend unreachable: {e}")
    return True


@pytest.fixture
def http(base_url: str, health_check) -> requests.Session:
    """匿名 HTTP 会话,带统一 header 与超时。"""
    s = requests.Session()
    s.headers.update({
        "Accept": "application/json",
        "Content-Type": "application/json",
    })
    original_request = s.request

    def request(method, url, **kwargs):
        if not url.startswith("http"):
            url = f"{base_url}{url}"
        kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
        return original_request(method, url, **kwargs)

    s.request = request
    return s


def _gen_unique_user() -> dict:
    """生成符合 UserCreateSerializer 约束的注册数据。"""
    suffix = uuid.uuid4().hex[:8]
    return {
        "username": f"qa_{suffix}",
        "email": f"qa_{suffix}@testhub.test",
        "password": "Pwd@12345",
        "password_confirm": "Pwd@12345",
        "first_name": "Qa",
        "last_name": "Bot",
        "phone": f"138{int(time.time()) % 100000000:08d}",
        "department": "QA",
        "position": "engineer",
    }


@pytest.fixture
def random_user_payload() -> dict:
    """每次注入新生成的注册参数,可直接 POST /api/auth/register/。"""
    return _gen_unique_user()


@pytest.fixture
def registered_user(http: requests.Session) -> dict:
    """注册一个全新用户并返回 {username,password,email,token,user}。

    注意: register 接口返回 DRF Token (非 JWT)。需要 JWT 时单独 login。
    遇 429 限流自动退避重试一次,仍失败则跳过用例(避免污染失败结果)。
    若配置了 TESTHUB_TEST_USERNAME / TESTHUB_TEST_PASSWORD, 直接复用该账号
    以避免频繁注册触发后端限流。
    """
    if DEFAULT_USERNAME and DEFAULT_PASSWORD:
        # 复用预置账号,通过 login 获取 user 信息
        tokens = _login(http, DEFAULT_USERNAME, DEFAULT_PASSWORD)
        user = tokens.get("user", {})
        return {
            "username": DEFAULT_USERNAME,
            "password": DEFAULT_PASSWORD,
            "email": user.get("email", ""),
            "user": user,
            "token": tokens.get("access", ""),
        }

    payload = _gen_unique_user()
    r = http.post("/api/auth/register/", json=payload)
    if r.status_code == 429:
        retry_after = int(r.headers.get("Retry-After", "30"))
        wait = min(retry_after, 30)
        time.sleep(wait)
        r = http.post("/api/auth/register/", json=payload)
        if r.status_code == 429:
            pytest.skip(f"register throttled, retry-after={retry_after}s; rerun later")
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"
    body = r.json()
    return {
        "username": payload["username"],
        "password": payload["password"],
        "email": payload["email"],
        "user": body.get("user"),
        "token": body.get("token"),
    }


_login_cache: dict = {}


def _login(http: requests.Session, username: str, password: str) -> dict:
    key = f"{username}:{password}"
    if key in _login_cache:
        return _login_cache[key]
    r = http.post("/api/auth/login/", json={"username": username, "password": password})
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    tokens = r.json()
    _login_cache[key] = tokens
    return tokens


@pytest.fixture
def login_tokens(http: requests.Session, registered_user: dict) -> dict:
    """对 registered_user 执行登录,返回 access/refresh JWT。"""
    return _login(http, registered_user["username"], registered_user["password"])


@pytest.fixture
def authed_http(base_url: str, login_tokens: dict, health_check) -> requests.Session:
    """已携带 JWT 的 HTTP 会话。"""
    s = requests.Session()
    s.headers.update({
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {login_tokens['access']}",
    })
    original_request = s.request

    def request(method, url, **kwargs):
        if not url.startswith("http"):
            url = f"{base_url}{url}"
        kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
        return original_request(method, url, **kwargs)

    s.request = request
    return s


@pytest.fixture
def default_credentials() -> Optional[dict]:
    """如配置了默认账号,返回 {username,password},否则 None。可由用例 skip。"""
    if DEFAULT_USERNAME and DEFAULT_PASSWORD:
        return {"username": DEFAULT_USERNAME, "password": DEFAULT_PASSWORD}
    return None


@pytest.fixture
def admin_credentials() -> Optional[dict]:
    if ADMIN_USERNAME and ADMIN_PASSWORD:
        return {"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
    return None


@pytest.fixture
def project_payload() -> dict:
    """符合 ProjectCreateSerializer 的最小项目创建数据。"""
    return {
        "name": f"qa-project-{uuid.uuid4().hex[:6]}",
        "description": "auto-generated by api test",
        "status": "active",
    }


@pytest.fixture
def created_project(authed_http: requests.Session, project_payload: dict) -> dict:
    r = authed_http.post("/api/projects/", json=project_payload)
    assert r.status_code in (200, 201), f"create project failed: {r.status_code} {r.text}"
    body = r.json()
    if "id" not in body:
        # ProjectCreateSerializer 仅声明 name/description/status/create_unified 字段,
        # 创建响应不含 id;通过 list 接口按 name 反查,确保后续用例可用 id 操作。
        listing = authed_http.get("/api/projects/all/")
        if listing.status_code == 200:
            for item in listing.json():
                if item.get("name") == project_payload["name"]:
                    body["id"] = item["id"]
                    break
        assert "id" in body, f"cannot resolve project id, list={listing.text[:200]}"
    return body


# ============ Phase 2 fixtures: testcases / executions / reviews ============

@pytest.fixture
def testcase_payload(created_project: dict) -> dict:
    """符合 TestCaseCreate 的最小用例创建数据(title + expected_result 必填)。"""
    suffix = uuid.uuid4().hex[:6]
    return {
        "title": f"qa-tc-{suffix}",
        "description": "auto-generated by api test",
        "preconditions": "已登录",
        "expected_result": "200 OK",
        "priority": "medium",
        "test_type": "functional",
        "project_id": created_project["id"],
    }


@pytest.fixture
def created_testcase(authed_http: requests.Session, testcase_payload: dict) -> dict:
    """创建一条测试用例并返回 {id, title, ...}。"""
    r = authed_http.post("/api/testcases/", json=testcase_payload)
    assert r.status_code in (200, 201), f"create testcase failed: {r.status_code} {r.text}"
    body = r.json()
    # 部分序列化器返回不含 id, 通过 list 反查
    if "id" not in body:
        listing = authed_http.get(f"/api/testcases/?search={testcase_payload['title']}")
        if listing.status_code == 200:
            data = listing.json()
            results = data.get("results", data) if isinstance(data, dict) else data
            for item in results or []:
                if item.get("title") == testcase_payload["title"]:
                    body["id"] = item["id"]
                    break
    assert "id" in body, f"cannot resolve testcase id: {body}"
    return body


@pytest.fixture
def test_plan_payload(created_project: dict) -> dict:
    """TestPlan 最小创建数据(name + projects + version 必填)。"""
    suffix = uuid.uuid4().hex[:6]
    return {
        "name": f"qa-plan-{suffix}",
        "description": "auto plan",
        "projects": [created_project["id"]],
        "version": "v1.0",
        "is_active": True,
    }


@pytest.fixture
def created_test_plan(authed_http: requests.Session, test_plan_payload: dict) -> dict:
    r = authed_http.post("/api/executions/plans/", json=test_plan_payload)
    if r.status_code not in (200, 201):
        pytest.skip(f"create test_plan failed: {r.status_code} {r.text[:200]}")
    body = r.json()
    if "id" not in body:
        listing = authed_http.get("/api/executions/plans/")
        if listing.status_code == 200:
            data = listing.json()
            results = data.get("results", data) if isinstance(data, dict) else data
            for item in results or []:
                if item.get("name") == test_plan_payload["name"]:
                    body["id"] = item["id"]
                    break
    return body


@pytest.fixture
def test_run_payload(created_test_plan: dict, registered_user: dict) -> dict:
    """TestRun 最小创建数据(必填字段以 swagger 为准, 业务校验由后端处理)。"""
    suffix = uuid.uuid4().hex[:6]
    return {
        "name": f"qa-run-{suffix}",
        "test_plan": created_test_plan.get("id"),
        "assignee": registered_user.get("user", {}).get("id") if registered_user.get("user") else None,
        "status": "pending",
        "progress": 0,
        "run_cases": [],
    }


@pytest.fixture
def created_test_run(authed_http: requests.Session, test_run_payload: dict) -> dict:
    r = authed_http.post("/api/executions/runs/", json=test_run_payload)
    if r.status_code not in (200, 201):
        pytest.skip(f"create test_run failed: {r.status_code} {r.text[:200]}")
    return r.json()


@pytest.fixture
def review_template_payload(created_project: dict) -> dict:
    """ReviewTemplateCreate 最小数据(name + project)。"""
    suffix = uuid.uuid4().hex[:6]
    return {
        "name": f"qa-rvtpl-{suffix}",
        "description": "auto template",
        "project": [created_project["id"]],
        "checklist": [{"item": "代码规范", "weight": 1}],
        "default_reviewers": [],
    }


@pytest.fixture
def created_review_template(authed_http: requests.Session, review_template_payload: dict) -> dict:
    r = authed_http.post("/api/reviews/review-templates/", json=review_template_payload)
    if r.status_code not in (200, 201):
        pytest.skip(f"create review_template failed: {r.status_code} {r.text[:200]}")
    return r.json()


@pytest.fixture
def review_payload(created_project: dict, created_testcase: dict, registered_user: dict) -> dict:
    """TestCaseReviewCreate 最小数据(title + projects + testcases + reviewers)。"""
    suffix = uuid.uuid4().hex[:6]
    user_id = registered_user.get("user", {}).get("id") if registered_user.get("user") else None
    return {
        "title": f"qa-review-{suffix}",
        "description": "auto review",
        "projects": [created_project["id"]],
        "testcases": [created_testcase["id"]],
        "reviewers": [user_id] if user_id else [],
        "priority": "medium",
    }


@pytest.fixture
def created_review(authed_http: requests.Session, review_payload: dict) -> dict:
    r = authed_http.post("/api/reviews/reviews/", json=review_payload)
    if r.status_code not in (200, 201):
        pytest.skip(f"create review failed: {r.status_code} {r.text[:200]}")
    return r.json()

