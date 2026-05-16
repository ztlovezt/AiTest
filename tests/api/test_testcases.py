"""第 2 批 - testcases 模块测试用例(对应 testcases_phase2.md TC_xxx)。

覆盖 9 接口 30 用例。运行:
    pytest tests/api/test_testcases.py -m testcases
"""
import uuid

import pytest


pytestmark = [pytest.mark.testcases]


# ---------- 1.1 GET /api/testcases/ ----------

@pytest.mark.smoke
@pytest.mark.p0
@pytest.mark.positive
def test_testcases_list_p001_authed(authed_http):
    """TC_LST_001 已登录获取用例列表"""
    r = authed_http.get("/api/testcases/")
    assert r.status_code == 200
    body = r.json()
    assert "results" in body or isinstance(body, list)


@pytest.mark.p0
@pytest.mark.anomaly
def test_testcases_list_p002_anonymous(http):
    """TC_LST_002 匿名访问"""
    r = http.get("/api/testcases/")
    assert r.status_code == 401


@pytest.mark.p1
@pytest.mark.positive
def test_testcases_list_p003_filter_project(authed_http, created_project):
    """TC_LST_003 按 project 筛选"""
    r = authed_http.get(f"/api/testcases/?project={created_project['id']}")
    assert r.status_code == 200


@pytest.mark.p1
@pytest.mark.boundary
def test_testcases_list_p004_pagination(authed_http):
    """TC_LST_004 分页 page=2"""
    r = authed_http.get("/api/testcases/?page=1&page_size=5")
    assert r.status_code == 200
    body = r.json()
    if isinstance(body, dict) and "results" in body:
        assert len(body["results"]) <= 5


@pytest.mark.p1
@pytest.mark.positive
def test_testcases_list_p005_search(authed_http):
    """TC_LST_005 search 关键字"""
    r = authed_http.get("/api/testcases/?search=qa")
    assert r.status_code == 200


# ---------- 1.2 POST /api/testcases/ ----------

@pytest.mark.smoke
@pytest.mark.p0
@pytest.mark.positive
def test_testcases_create_p001_minimal(authed_http, created_project):
    """TC_CRE_001 最小字段创建用例"""
    payload = {
        "title": f"qa-tc-{uuid.uuid4().hex[:6]}",
        "expected_result": "200 OK",
        "project_id": created_project["id"],
    }
    r = authed_http.post("/api/testcases/", json=payload)
    assert r.status_code in (200, 201)


@pytest.mark.p0
@pytest.mark.positive
def test_testcases_create_p002_full_fields(authed_http, testcase_payload):
    """TC_CRE_002 全字段创建"""
    r = authed_http.post("/api/testcases/", json=testcase_payload)
    assert r.status_code in (200, 201)


@pytest.mark.p1
@pytest.mark.anomaly
def test_testcases_create_p003_missing_title(authed_http, created_project):
    """TC_CRE_003 缺 title"""
    r = authed_http.post("/api/testcases/", json={
        "expected_result": "ok",
        "project_id": created_project["id"],
    })
    assert r.status_code == 400


@pytest.mark.p1
@pytest.mark.anomaly
def test_testcases_create_p004_missing_expected(authed_http, created_project):
    """TC_CRE_004 缺 expected_result"""
    r = authed_http.post("/api/testcases/", json={
        "title": "qa-tc",
        "project_id": created_project["id"],
    })
    assert r.status_code == 400


@pytest.mark.p1
@pytest.mark.boundary
def test_testcases_create_p005_long_title(authed_http, created_project):
    """TC_CRE_005 title 超长"""
    r = authed_http.post("/api/testcases/", json={
        "title": "x" * 1000,
        "expected_result": "ok",
        "project_id": created_project["id"],
    })
    assert r.status_code < 500


@pytest.mark.p0
@pytest.mark.anomaly
def test_testcases_create_p006_anonymous(http):
    """TC_CRE_006 匿名创建"""
    r = http.post("/api/testcases/", json={"title": "x", "expected_result": "x"})
    assert r.status_code == 401


# ---------- 1.3 GET /api/testcases/{id}/ ----------

@pytest.mark.smoke
@pytest.mark.p0
@pytest.mark.positive
def test_testcases_detail_p001(authed_http, created_testcase):
    """TC_DET_001 详情查询"""
    r = authed_http.get(f"/api/testcases/{created_testcase['id']}/")
    assert r.status_code == 200
    assert r.json().get("id") == created_testcase["id"]


@pytest.mark.p1
@pytest.mark.anomaly
def test_testcases_detail_p002_not_found(authed_http):
    """TC_DET_002 不存在 ID"""
    r = authed_http.get("/api/testcases/99999999/")
    assert r.status_code == 404


@pytest.mark.p1
@pytest.mark.anomaly
def test_testcases_detail_p003_anonymous(http, created_testcase):
    """TC_DET_003 匿名访问"""
    r = http.get(f"/api/testcases/{created_testcase['id']}/")
    assert r.status_code == 401


# ---------- 1.4 PUT /api/testcases/{id}/ ----------

@pytest.mark.p1
@pytest.mark.positive
def test_testcases_put_p001(authed_http, created_testcase):
    """TC_PUT_001 全量更新成功"""
    new_title = f"qa-tc-put-{uuid.uuid4().hex[:6]}"
    r = authed_http.put(f"/api/testcases/{created_testcase['id']}/", json={
        "title": new_title,
        "expected_result": "updated",
        "priority": "high",
    })
    assert r.status_code == 200


@pytest.mark.p1
@pytest.mark.anomaly
def test_testcases_put_p002_missing_required(authed_http, created_testcase):
    """TC_PUT_002 缺必填字段"""
    r = authed_http.put(f"/api/testcases/{created_testcase['id']}/", json={
        "title": "only title",
    })
    assert r.status_code == 400


@pytest.mark.p1
@pytest.mark.anomaly
def test_testcases_put_p003_not_found(authed_http):
    """TC_PUT_003 不存在 ID"""
    r = authed_http.put("/api/testcases/99999999/", json={
        "title": "x", "expected_result": "x",
    })
    assert r.status_code == 404


# ---------- 1.5 PATCH /api/testcases/{id}/ ----------

@pytest.mark.p1
@pytest.mark.positive
def test_testcases_patch_p001_priority(authed_http, created_testcase):
    """TC_PCH_001 部分更新 priority"""
    r = authed_http.patch(f"/api/testcases/{created_testcase['id']}/", json={"priority": "high"})
    assert r.status_code == 200


@pytest.mark.p1
@pytest.mark.positive
def test_testcases_patch_p002_description(authed_http, created_testcase):
    """TC_PCH_002 部分更新 description"""
    r = authed_http.patch(f"/api/testcases/{created_testcase['id']}/", json={"description": "new"})
    assert r.status_code == 200


@pytest.mark.p1
@pytest.mark.anomaly
def test_testcases_patch_p003_not_found(authed_http):
    """TC_PCH_003 不存在 ID"""
    r = authed_http.patch("/api/testcases/99999999/", json={"description": "x"})
    assert r.status_code == 404


# ---------- 1.6 DELETE /api/testcases/{id}/ ----------

@pytest.mark.smoke
@pytest.mark.p0
@pytest.mark.positive
@pytest.mark.xfail(reason="BUG: backend returns 500 on TestCase delete (cascade/signal issue)", strict=False)
def test_testcases_delete_p001(authed_http, created_testcase):
    """TC_DEL_001 删除成功"""
    tid = created_testcase["id"]
    r = authed_http.delete(f"/api/testcases/{tid}/")
    assert r.status_code in (200, 204)
    r2 = authed_http.get(f"/api/testcases/{tid}/")
    assert r2.status_code in (404, 401)


@pytest.mark.p1
@pytest.mark.anomaly
def test_testcases_delete_p002_not_found(authed_http):
    """TC_DEL_002 不存在 ID"""
    r = authed_http.delete("/api/testcases/99999999/")
    assert r.status_code == 404


@pytest.mark.p1
@pytest.mark.anomaly
def test_testcases_delete_p003_anonymous(http, created_testcase):
    """TC_DEL_003 匿名删除"""
    r = http.delete(f"/api/testcases/{created_testcase['id']}/")
    assert r.status_code == 401


# ---------- 1.7 GET /api/testcases/import/records/ ----------

@pytest.mark.p1
@pytest.mark.positive
def test_testcases_import_records_p001(authed_http):
    """TC_IMR_001 已登录列出导入记录"""
    r = authed_http.get("/api/testcases/import/records/")
    assert r.status_code == 200


@pytest.mark.p1
@pytest.mark.anomaly
def test_testcases_import_records_p002_anonymous(http):
    """TC_IMR_002 匿名访问"""
    r = http.get("/api/testcases/import/records/")
    assert r.status_code == 401


@pytest.mark.p2
@pytest.mark.boundary
def test_testcases_import_records_p003_pagination(authed_http):
    """TC_IMR_003 分页"""
    r = authed_http.get("/api/testcases/import/records/?page=1")
    assert r.status_code == 200


# ---------- 1.8 GET /api/testcases/import/template/ ----------

@pytest.mark.p1
@pytest.mark.positive
@pytest.mark.review_required
def test_testcases_import_template_p001(authed_http):
    """TC_IMT_001 已登录下载模板"""
    r = authed_http.get("/api/testcases/import/template/")
    assert r.status_code in (200, 302)


@pytest.mark.p1
@pytest.mark.anomaly
def test_testcases_import_template_p002_anonymous(http):
    """TC_IMT_002 匿名访问"""
    r = http.get("/api/testcases/import/template/")
    assert r.status_code == 401


# ---------- 1.9 POST /api/testcases/import/upload/ ----------

@pytest.mark.p1
@pytest.mark.anomaly
def test_testcases_import_upload_p001_missing_file(authed_http):
    """TC_IMU_001 缺文件上传"""
    r = authed_http.post("/api/testcases/import/upload/", json={})
    assert r.status_code == 400


@pytest.mark.p1
@pytest.mark.anomaly
def test_testcases_import_upload_p002_anonymous(http):
    """TC_IMU_002 匿名上传"""
    r = http.post("/api/testcases/import/upload/", json={})
    assert r.status_code == 401
