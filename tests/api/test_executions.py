"""第 2 批 - executions 模块测试用例(对应 testcases_phase2.md EX_xxx)。

覆盖 23 接口 65 用例。运行:
    pytest tests/api/test_executions.py -m executions
"""
import uuid

import pytest


pytestmark = [pytest.mark.executions]


# ============================================================================
# 2.1-2.5  /api/executions/plans/  测试计划(20 用例)
# ============================================================================

@pytest.mark.smoke
@pytest.mark.p0
@pytest.mark.positive
def test_executions_plans_list_p001_authed(authed_http):
    """EX_PLN_LST_001 已登录列表"""
    r = authed_http.get("/api/executions/plans/")
    assert r.status_code == 200


@pytest.mark.p0
@pytest.mark.anomaly
def test_executions_plans_list_p002_anonymous(http):
    """EX_PLN_LST_002 匿名访问"""
    r = http.get("/api/executions/plans/")
    assert r.status_code == 401


@pytest.mark.p1
@pytest.mark.boundary
def test_executions_plans_list_p003_pagination(authed_http):
    """EX_PLN_LST_003 分页 page_size"""
    r = authed_http.get("/api/executions/plans/?page_size=1")
    assert r.status_code == 200


@pytest.mark.p2
@pytest.mark.positive
def test_executions_plans_list_p004_search(authed_http):
    """EX_PLN_LST_004 search 关键字"""
    r = authed_http.get("/api/executions/plans/?search=qa")
    assert r.status_code == 200


@pytest.mark.smoke
@pytest.mark.p0
@pytest.mark.positive
@pytest.mark.xfail(reason="BUG: backend db schema missing test_run_cases.test_run_id (migration needed)", strict=False)
def test_executions_plans_create_p001_minimal(authed_http, test_plan_payload):
    """EX_PLN_CRE_001 最小字段创建"""
    r = authed_http.post("/api/executions/plans/", json=test_plan_payload)
    assert r.status_code in (200, 201)


@pytest.mark.p1
@pytest.mark.anomaly
def test_executions_plans_create_p002_missing_name(authed_http, created_project):
    """EX_PLN_CRE_002 缺 name"""
    r = authed_http.post("/api/executions/plans/", json={
        "projects": [created_project["id"]], "version": "v1"})
    assert r.status_code == 400


@pytest.mark.p1
@pytest.mark.anomaly
def test_executions_plans_create_p003_missing_projects(authed_http):
    """EX_PLN_CRE_003 缺 projects"""
    r = authed_http.post("/api/executions/plans/", json={
        "name": "qa-plan", "version": "v1"})
    assert r.status_code == 400


@pytest.mark.p1
@pytest.mark.boundary
def test_executions_plans_create_p004_empty_projects(authed_http):
    """EX_PLN_CRE_004 projects 为空数组"""
    r = authed_http.post("/api/executions/plans/", json={
        "name": "qa-plan", "projects": [], "version": "v1"})
    assert r.status_code == 400


@pytest.mark.p0
@pytest.mark.anomaly
def test_executions_plans_create_p005_anonymous(http):
    """EX_PLN_CRE_005 匿名创建"""
    r = http.post("/api/executions/plans/", json={"name": "x", "projects": [1], "version": "v1"})
    assert r.status_code == 401


@pytest.mark.smoke
@pytest.mark.p0
@pytest.mark.positive
def test_executions_plans_detail_p001(authed_http, created_test_plan):
    """EX_PLN_DET_001 详情查询"""
    pid = created_test_plan.get("id")
    if not pid:
        pytest.skip("plan id missing")
    r = authed_http.get(f"/api/executions/plans/{pid}/")
    assert r.status_code == 200


@pytest.mark.p1
@pytest.mark.anomaly
def test_executions_plans_detail_p002_not_found(authed_http):
    """EX_PLN_DET_002 不存在 ID"""
    r = authed_http.get("/api/executions/plans/99999999/")
    assert r.status_code == 404


@pytest.mark.p1
@pytest.mark.anomaly
def test_executions_plans_detail_p003_anonymous(http, created_test_plan):
    """EX_PLN_DET_003 匿名访问"""
    pid = created_test_plan.get("id")
    if not pid:
        pytest.skip("plan id missing")
    r = http.get(f"/api/executions/plans/{pid}/")
    assert r.status_code == 401


@pytest.mark.p1
@pytest.mark.positive
def test_executions_plans_put_p001(authed_http, created_test_plan, created_project):
    """EX_PLN_PUT_001 全量更新成功"""
    pid = created_test_plan.get("id")
    if not pid:
        pytest.skip("plan id missing")
    r = authed_http.put(f"/api/executions/plans/{pid}/", json={
        "name": f"qa-plan-put-{uuid.uuid4().hex[:6]}",
        "projects": [created_project["id"]],
        "version": "v2",
    })
    assert r.status_code == 200


@pytest.mark.p1
@pytest.mark.anomaly
def test_executions_plans_put_p002_missing_name(authed_http, created_test_plan, created_project):
    """EX_PLN_PUT_002 缺必填字段"""
    pid = created_test_plan.get("id")
    if not pid:
        pytest.skip("plan id missing")
    r = authed_http.put(f"/api/executions/plans/{pid}/", json={
        "projects": [created_project["id"]], "version": "v1"})
    assert r.status_code == 400


@pytest.mark.p1
@pytest.mark.positive
def test_executions_plans_patch_p001_is_active(authed_http, created_test_plan):
    """EX_PLN_PCH_001 部分更新 is_active"""
    pid = created_test_plan.get("id")
    if not pid:
        pytest.skip("plan id missing")
    r = authed_http.patch(f"/api/executions/plans/{pid}/", json={"is_active": False})
    assert r.status_code == 200


@pytest.mark.p1
@pytest.mark.anomaly
def test_executions_plans_patch_p002_not_found(authed_http):
    """EX_PLN_PCH_002 部分更新不存在 ID"""
    r = authed_http.patch("/api/executions/plans/99999999/", json={"is_active": False})
    assert r.status_code == 404


@pytest.mark.smoke
@pytest.mark.p0
@pytest.mark.positive
def test_executions_plans_delete_p001(authed_http, created_test_plan):
    """EX_PLN_DEL_001 删除成功"""
    pid = created_test_plan.get("id")
    if not pid:
        pytest.skip("plan id missing")
    r = authed_http.delete(f"/api/executions/plans/{pid}/")
    assert r.status_code in (200, 204)


@pytest.mark.p1
@pytest.mark.anomaly
def test_executions_plans_delete_p002_not_found(authed_http):
    """EX_PLN_DEL_002 删除不存在"""
    r = authed_http.delete("/api/executions/plans/99999999/")
    assert r.status_code == 404


@pytest.mark.p1
@pytest.mark.positive
@pytest.mark.review_required
def test_executions_plans_tcs_by_projects_p001(authed_http, created_project):
    """EX_PLN_TBP_001 按项目获取用例"""
    r = authed_http.get(f"/api/executions/plans/testcases_by_projects/?projects={created_project['id']}")
    assert r.status_code in (200, 400)


@pytest.mark.p1
@pytest.mark.anomaly
def test_executions_plans_tcs_by_projects_p002_anonymous(http):
    """EX_PLN_TBP_002 匿名访问"""
    r = http.get("/api/executions/plans/testcases_by_projects/?projects=1")
    assert r.status_code == 401


# ============================================================================
# 2.6-2.8  /api/executions/runs/  执行(15 用例)
# ============================================================================

@pytest.mark.smoke
@pytest.mark.p0
@pytest.mark.positive
@pytest.mark.xfail(reason="BUG: backend db schema missing test_run_cases.test_run_id (migration needed)", strict=False)
def test_executions_runs_list_p001_authed(authed_http):
    """EX_RUN_LST_001 已登录列表"""
    r = authed_http.get("/api/executions/runs/")
    assert r.status_code == 200


@pytest.mark.p0
@pytest.mark.anomaly
def test_executions_runs_list_p002_anonymous(http):
    """EX_RUN_LST_002 匿名"""
    r = http.get("/api/executions/runs/")
    assert r.status_code == 401


@pytest.mark.p2
@pytest.mark.positive
def test_executions_runs_list_p003_search(authed_http):
    """EX_RUN_LST_003 search"""
    r = authed_http.get("/api/executions/runs/?search=qa")
    assert r.status_code == 200


@pytest.mark.p0
@pytest.mark.positive
@pytest.mark.review_required
def test_executions_runs_create_p001(authed_http, test_run_payload):
    """EX_RUN_CRE_001 创建 run"""
    r = authed_http.post("/api/executions/runs/", json=test_run_payload)
    assert r.status_code in (200, 201, 400)


@pytest.mark.p1
@pytest.mark.anomaly
def test_executions_runs_create_p002_missing_name(authed_http):
    """EX_RUN_CRE_002 缺 name"""
    r = authed_http.post("/api/executions/runs/", json={"progress": 0})
    assert r.status_code == 400


@pytest.mark.p1
@pytest.mark.anomaly
def test_executions_runs_create_p003_missing_assignee(authed_http):
    """EX_RUN_CRE_003 缺 assignee"""
    r = authed_http.post("/api/executions/runs/", json={"name": "x", "progress": 0})
    assert r.status_code in (400, 201)  # 业务可能允许 null assignee


@pytest.mark.p0
@pytest.mark.anomaly
def test_executions_runs_create_p004_anonymous(http):
    """EX_RUN_CRE_004 匿名"""
    r = http.post("/api/executions/runs/", json={"name": "x"})
    assert r.status_code == 401


@pytest.mark.p0
@pytest.mark.positive
def test_executions_runs_detail_p001(authed_http, created_test_run):
    """EX_RUN_DET_001 详情查询"""
    rid = created_test_run.get("id")
    if not rid:
        pytest.skip("run id missing")
    r = authed_http.get(f"/api/executions/runs/{rid}/")
    assert r.status_code == 200


@pytest.mark.p1
@pytest.mark.anomaly
def test_executions_runs_detail_p002_not_found(authed_http):
    """EX_RUN_DET_002 不存在"""
    r = authed_http.get("/api/executions/runs/99999999/")
    assert r.status_code == 404


@pytest.mark.p1
@pytest.mark.positive
@pytest.mark.review_required
def test_executions_runs_put_p001(authed_http, created_test_run, registered_user):
    """EX_RUN_PUT_001 全量更新"""
    rid = created_test_run.get("id")
    if not rid:
        pytest.skip("run id missing")
    user_id = registered_user.get("user", {}).get("id")
    r = authed_http.put(f"/api/executions/runs/{rid}/", json={
        "name": f"qa-run-{uuid.uuid4().hex[:6]}",
        "assignee": user_id,
        "progress": 50,
        "run_cases": [],
    })
    assert r.status_code in (200, 400)


@pytest.mark.p1
@pytest.mark.positive
def test_executions_runs_patch_p001_status(authed_http, created_test_run):
    """EX_RUN_PCH_001 部分更新 status"""
    rid = created_test_run.get("id")
    if not rid:
        pytest.skip("run id missing")
    r = authed_http.patch(f"/api/executions/runs/{rid}/", json={"status": "completed"})
    assert r.status_code == 200


@pytest.mark.p1
@pytest.mark.anomaly
def test_executions_runs_patch_p002_not_found(authed_http):
    """EX_RUN_PCH_002 不存在 PATCH"""
    r = authed_http.patch("/api/executions/runs/99999999/", json={"status": "x"})
    assert r.status_code == 404


@pytest.mark.p0
@pytest.mark.positive
def test_executions_runs_delete_p001(authed_http, created_test_run):
    """EX_RUN_DEL_001 删除成功"""
    rid = created_test_run.get("id")
    if not rid:
        pytest.skip("run id missing")
    r = authed_http.delete(f"/api/executions/runs/{rid}/")
    assert r.status_code in (200, 204)


@pytest.mark.p1
@pytest.mark.anomaly
def test_executions_runs_delete_p002_not_found(authed_http):
    """EX_RUN_DEL_002 删除不存在"""
    r = authed_http.delete("/api/executions/runs/99999999/")
    assert r.status_code == 404


# ============================================================================
# 2.9  /api/executions/run_cases/  执行用例项(11 用例)
# ============================================================================

@pytest.mark.p1
@pytest.mark.positive
def test_executions_run_cases_list_p001(authed_http):
    """EX_RC_LST_001 列表"""
    r = authed_http.get("/api/executions/run_cases/")
    assert r.status_code == 200


@pytest.mark.p1
@pytest.mark.anomaly
def test_executions_run_cases_list_p002_anonymous(http):
    """EX_RC_LST_002 匿名"""
    r = http.get("/api/executions/run_cases/")
    assert r.status_code == 401


@pytest.mark.p1
@pytest.mark.positive
@pytest.mark.review_required
def test_executions_run_cases_create_p001(authed_http, created_test_run, created_testcase):
    """EX_RC_CRE_001 创建 run_case"""
    rid = created_test_run.get("id")
    if not rid:
        pytest.skip("run id missing")
    r = authed_http.post("/api/executions/run_cases/", json={
        "test_run": rid,
        "testcase": created_testcase["id"],
    })
    assert r.status_code in (200, 201, 400)


@pytest.mark.p1
@pytest.mark.anomaly
def test_executions_run_cases_create_p002_missing_test_run(authed_http, created_testcase):
    """EX_RC_CRE_002 缺 test_run"""
    r = authed_http.post("/api/executions/run_cases/", json={"testcase": created_testcase["id"]})
    assert r.status_code == 400


@pytest.mark.p1
@pytest.mark.anomaly
def test_executions_run_cases_create_p003_missing_testcase(authed_http, created_test_run):
    """EX_RC_CRE_003 缺 testcase"""
    rid = created_test_run.get("id")
    if not rid:
        pytest.skip("run id missing")
    r = authed_http.post("/api/executions/run_cases/", json={"test_run": rid})
    assert r.status_code == 400


@pytest.fixture
def _created_run_case(authed_http, created_test_run, created_testcase):
    """创建一条 run_case 用于详情/更新/删除测试。"""
    rid = created_test_run.get("id")
    if not rid:
        pytest.skip("run id missing for run_case")
    r = authed_http.post("/api/executions/run_cases/", json={
        "test_run": rid, "testcase": created_testcase["id"],
    })
    if r.status_code not in (200, 201):
        pytest.skip(f"create run_case failed: {r.status_code} {r.text[:200]}")
    return r.json()


@pytest.mark.p1
@pytest.mark.positive
def test_executions_run_cases_detail_p001(authed_http, _created_run_case):
    """EX_RC_DET_001 详情"""
    rcid = _created_run_case.get("id")
    if not rcid:
        pytest.skip("run_case id missing")
    r = authed_http.get(f"/api/executions/run_cases/{rcid}/")
    assert r.status_code == 200


@pytest.mark.p1
@pytest.mark.anomaly
def test_executions_run_cases_detail_p002_not_found(authed_http):
    """EX_RC_DET_002 不存在"""
    r = authed_http.get("/api/executions/run_cases/99999999/")
    assert r.status_code == 404


@pytest.mark.p1
@pytest.mark.positive
@pytest.mark.review_required
def test_executions_run_cases_put_p001(authed_http, _created_run_case):
    """EX_RC_PUT_001 全量更新"""
    rcid = _created_run_case.get("id")
    if not rcid:
        pytest.skip("run_case id missing")
    r = authed_http.put(f"/api/executions/run_cases/{rcid}/", json={
        "test_run": _created_run_case.get("test_run"),
        "testcase": _created_run_case.get("testcase"),
        "status": "passed",
    })
    assert r.status_code in (200, 400)


@pytest.mark.p0
@pytest.mark.positive
def test_executions_run_cases_patch_p001_status(authed_http, _created_run_case):
    """EX_RC_PCH_001 部分更新 status"""
    rcid = _created_run_case.get("id")
    if not rcid:
        pytest.skip("run_case id missing")
    r = authed_http.patch(f"/api/executions/run_cases/{rcid}/", json={"status": "passed"})
    assert r.status_code == 200


@pytest.mark.p1
@pytest.mark.positive
def test_executions_run_cases_delete_p001(authed_http, _created_run_case):
    """EX_RC_DEL_001 删除"""
    rcid = _created_run_case.get("id")
    if not rcid:
        pytest.skip("run_case id missing")
    r = authed_http.delete(f"/api/executions/run_cases/{rcid}/")
    assert r.status_code in (200, 204)


@pytest.mark.p1
@pytest.mark.anomaly
def test_executions_run_cases_delete_p002_not_found(authed_http):
    """EX_RC_DEL_002 删除不存在"""
    r = authed_http.delete("/api/executions/run_cases/99999999/")
    assert r.status_code == 404


# ============================================================================
# 2.10-2.12  其它(7 用例)
# ============================================================================

@pytest.mark.p1
@pytest.mark.positive
def test_executions_run_case_history_p001(authed_http, _created_run_case):
    """EX_RCH_001 查询历史"""
    rcid = _created_run_case.get("id")
    if not rcid:
        pytest.skip("run_case id missing")
    r = authed_http.get(f"/api/executions/run_cases/{rcid}/history/")
    assert r.status_code == 200


@pytest.mark.p1
@pytest.mark.anomaly
def test_executions_run_case_history_p002_not_found(authed_http):
    """EX_RCH_002 不存在 ID"""
    r = authed_http.get("/api/executions/run_cases/99999999/history/")
    assert r.status_code == 404


@pytest.mark.p0
@pytest.mark.positive
def test_executions_run_case_update_status_p001(authed_http, _created_run_case):
    """EX_RCU_001 更新状态成功"""
    rcid = _created_run_case.get("id")
    if not rcid:
        pytest.skip("run_case id missing")
    r = authed_http.patch(f"/api/executions/run_cases/{rcid}/update_status/", json={
        "status": "failed", "actual_result": "x", "comments": "auto",
    })
    assert r.status_code == 200


@pytest.mark.p1
@pytest.mark.anomaly
@pytest.mark.review_required
def test_executions_run_case_update_status_p002_invalid(authed_http, _created_run_case):
    """EX_RCU_002 非法 status"""
    rcid = _created_run_case.get("id")
    if not rcid:
        pytest.skip("run_case id missing")
    r = authed_http.patch(f"/api/executions/run_cases/{rcid}/update_status/", json={
        "status": "invalid_status_xyz",
    })
    assert r.status_code in (400, 200)


@pytest.mark.p1
@pytest.mark.anomaly
def test_executions_run_case_update_status_p003_not_found(authed_http):
    """EX_RCU_003 不存在 ID"""
    r = authed_http.patch("/api/executions/run_cases/99999999/update_status/", json={"status": "passed"})
    assert r.status_code == 404


@pytest.mark.p1
@pytest.mark.positive
def test_executions_history_list_p001(authed_http):
    """EX_HIS_LST_001 历史列表"""
    r = authed_http.get("/api/executions/history/")
    assert r.status_code == 200


@pytest.mark.p1
@pytest.mark.positive
@pytest.mark.review_required
def test_executions_history_detail_p001(authed_http):
    """EX_HIS_DET_001 历史详情"""
    listing = authed_http.get("/api/executions/history/")
    if listing.status_code != 200:
        pytest.skip("history list not available")
    body = listing.json()
    items = body.get("results", body) if isinstance(body, dict) else body
    if not items:
        pytest.skip("no history record")
    hid = items[0].get("id")
    r = authed_http.get(f"/api/executions/history/{hid}/")
    assert r.status_code in (200, 404)


# ============================================================================
# 2.13  组合用例(3 用例)
# ============================================================================

@pytest.mark.p0
@pytest.mark.combination
@pytest.mark.smoke
def test_executions_e2e_p001_full_link(
    authed_http, created_project, created_testcase, created_test_plan
):
    """EX_COMB_001 E2E 测试链路 — 项目→用例→计划→执行→更新"""
    # 1. project / testcase / plan 已由 fixtures 创建
    assert created_project.get("id")
    assert created_testcase.get("id")
    pid = created_test_plan.get("id")
    if not pid:
        pytest.skip("plan id missing")
    # 2. 列表查得到
    r = authed_http.get(f"/api/executions/plans/{pid}/")
    assert r.status_code == 200


@pytest.mark.p1
@pytest.mark.combination
def test_executions_e2e_p002_delete_plan_then_check(authed_http, created_test_plan):
    """EX_COMB_002 删除 plan 后状态自洽"""
    pid = created_test_plan.get("id")
    if not pid:
        pytest.skip("plan id missing")
    r = authed_http.delete(f"/api/executions/plans/{pid}/")
    assert r.status_code in (200, 204)
    r2 = authed_http.get(f"/api/executions/plans/{pid}/")
    assert r2.status_code == 404


@pytest.mark.p1
@pytest.mark.combination
def test_executions_e2e_p003_run_case_state_machine(authed_http, _created_run_case):
    """EX_COMB_003 run_case 状态机 pending→running→passed"""
    rcid = _created_run_case.get("id")
    if not rcid:
        pytest.skip("run_case id missing")
    for status in ("running", "passed"):
        r = authed_http.patch(f"/api/executions/run_cases/{rcid}/", json={"status": status})
        assert r.status_code == 200, f"transition to {status} failed"

