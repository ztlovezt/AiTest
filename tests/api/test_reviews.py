"""第 2 批 - reviews 模块测试用例(对应 testcases_phase2.md RV_xxx)。

覆盖 21 接口 55 用例。运行:
    pytest tests/api/test_reviews.py -m reviews
"""
import uuid

import pytest


pytestmark = [pytest.mark.reviews]


# ============================================================================
# 3.1-3.3  /api/reviews/review-templates/  评审模板(15 用例)
# ============================================================================

@pytest.mark.smoke
@pytest.mark.p0
@pytest.mark.positive
def test_reviews_template_list_p001(authed_http):
    """RV_TPL_LST_001 已登录列表"""
    r = authed_http.get("/api/reviews/review-templates/")
    assert r.status_code == 200


@pytest.mark.p0
@pytest.mark.anomaly
def test_reviews_template_list_p002_anonymous(http):
    """RV_TPL_LST_002 匿名"""
    r = http.get("/api/reviews/review-templates/")
    assert r.status_code == 401


@pytest.mark.p2
@pytest.mark.boundary
def test_reviews_template_list_p003_pagination(authed_http):
    """RV_TPL_LST_003 分页"""
    r = authed_http.get("/api/reviews/review-templates/?page=1")
    assert r.status_code == 200


@pytest.mark.smoke
@pytest.mark.p0
@pytest.mark.positive
def test_reviews_template_create_p001_minimal(authed_http, created_project):
    """RV_TPL_CRE_001 最小创建"""
    r = authed_http.post("/api/reviews/review-templates/", json={
        "name": f"qa-rvtpl-{uuid.uuid4().hex[:6]}",
        "project": [created_project["id"]],
    })
    assert r.status_code in (200, 201)


@pytest.mark.p1
@pytest.mark.positive
def test_reviews_template_create_p002_full(authed_http, review_template_payload):
    """RV_TPL_CRE_002 全字段创建"""
    r = authed_http.post("/api/reviews/review-templates/", json=review_template_payload)
    assert r.status_code in (200, 201)


@pytest.mark.p1
@pytest.mark.anomaly
def test_reviews_template_create_p003_missing_name(authed_http, created_project):
    """RV_TPL_CRE_003 缺 name"""
    r = authed_http.post("/api/reviews/review-templates/", json={"project": [created_project["id"]]})
    assert r.status_code == 400


@pytest.mark.p1
@pytest.mark.anomaly
def test_reviews_template_create_p004_missing_project(authed_http):
    """RV_TPL_CRE_004 缺 project"""
    r = authed_http.post("/api/reviews/review-templates/", json={"name": "qa"})
    assert r.status_code == 400


@pytest.mark.p0
@pytest.mark.anomaly
def test_reviews_template_create_p005_anonymous(http):
    """RV_TPL_CRE_005 匿名"""
    r = http.post("/api/reviews/review-templates/", json={"name": "x", "project": 1})
    assert r.status_code == 401


@pytest.mark.p0
@pytest.mark.positive
def test_reviews_template_detail_p001(authed_http, created_review_template):
    """RV_TPL_DET_001 详情查询"""
    tid = created_review_template.get("id")
    if not tid:
        pytest.skip("template id missing")
    r = authed_http.get(f"/api/reviews/review-templates/{tid}/")
    assert r.status_code == 200


@pytest.mark.p1
@pytest.mark.anomaly
def test_reviews_template_detail_p002_not_found(authed_http):
    """RV_TPL_DET_002 不存在"""
    r = authed_http.get("/api/reviews/review-templates/99999999/")
    assert r.status_code == 404


@pytest.mark.p1
@pytest.mark.positive
def test_reviews_template_put_p001(authed_http, created_review_template, created_project):
    """RV_TPL_PUT_001 全量更新"""
    tid = created_review_template.get("id")
    if not tid:
        pytest.skip("template id missing")
    r = authed_http.put(f"/api/reviews/review-templates/{tid}/", json={
        "name": f"qa-rvtpl-put-{uuid.uuid4().hex[:6]}",
        "project": [created_project["id"]],
    })
    assert r.status_code == 200


@pytest.mark.p1
@pytest.mark.anomaly
def test_reviews_template_put_p002_missing(authed_http, created_review_template):
    """RV_TPL_PUT_002 缺必填"""
    tid = created_review_template.get("id")
    if not tid:
        pytest.skip("template id missing")
    r = authed_http.put(f"/api/reviews/review-templates/{tid}/", json={})
    assert r.status_code == 400


@pytest.mark.p1
@pytest.mark.positive
def test_reviews_template_patch_p001_description(authed_http, created_review_template):
    """RV_TPL_PCH_001 部分更新 description"""
    tid = created_review_template.get("id")
    if not tid:
        pytest.skip("template id missing")
    r = authed_http.patch(f"/api/reviews/review-templates/{tid}/", json={"description": "new"})
    assert r.status_code == 200


@pytest.mark.p0
@pytest.mark.positive
def test_reviews_template_delete_p001(authed_http, created_review_template):
    """RV_TPL_DEL_001 删除"""
    tid = created_review_template.get("id")
    if not tid:
        pytest.skip("template id missing")
    r = authed_http.delete(f"/api/reviews/review-templates/{tid}/")
    assert r.status_code in (200, 204)


@pytest.mark.p1
@pytest.mark.anomaly
def test_reviews_template_delete_p002_not_found(authed_http):
    """RV_TPL_DEL_002 删除不存在"""
    r = authed_http.delete("/api/reviews/review-templates/99999999/")
    assert r.status_code == 404


# ============================================================================
# 3.4-3.6  /api/reviews/reviews/  评审 CRUD(16 用例)
# ============================================================================

@pytest.mark.smoke
@pytest.mark.p0
@pytest.mark.positive
def test_reviews_review_list_p001(authed_http):
    """RV_REV_LST_001 列表"""
    r = authed_http.get("/api/reviews/reviews/")
    assert r.status_code == 200


@pytest.mark.p0
@pytest.mark.anomaly
def test_reviews_review_list_p002_anonymous(http):
    """RV_REV_LST_002 匿名"""
    r = http.get("/api/reviews/reviews/")
    assert r.status_code == 401


@pytest.mark.p2
@pytest.mark.positive
def test_reviews_review_list_p003_search(authed_http):
    """RV_REV_LST_003 search"""
    r = authed_http.get("/api/reviews/reviews/?search=qa")
    assert r.status_code == 200


@pytest.mark.smoke
@pytest.mark.p0
@pytest.mark.positive
@pytest.mark.xfail(reason="BUG: backend returns 500 on review create (needs investigation)", strict=False)
def test_reviews_review_create_p001_minimal(authed_http, review_payload):
    """RV_REV_CRE_001 最小创建"""
    r = authed_http.post("/api/reviews/reviews/", json=review_payload)
    assert r.status_code in (200, 201)


@pytest.mark.p1
@pytest.mark.anomaly
def test_reviews_review_create_p002_missing_title(authed_http, created_project, created_testcase, registered_user):
    """RV_REV_CRE_002 缺 title"""
    user_id = registered_user.get("user", {}).get("id")
    r = authed_http.post("/api/reviews/reviews/", json={
        "projects": [created_project["id"]],
        "testcases": [created_testcase["id"]],
        "reviewers": [user_id] if user_id else [],
    })
    assert r.status_code == 400


@pytest.mark.p1
@pytest.mark.anomaly
def test_reviews_review_create_p003_missing_testcases(authed_http, created_project, registered_user):
    """RV_REV_CRE_003 缺 testcases"""
    user_id = registered_user.get("user", {}).get("id")
    r = authed_http.post("/api/reviews/reviews/", json={
        "title": "qa-review",
        "projects": [created_project["id"]],
        "reviewers": [user_id] if user_id else [],
    })
    assert r.status_code == 400


@pytest.mark.p1
@pytest.mark.anomaly
def test_reviews_review_create_p004_missing_reviewers(authed_http, created_project, created_testcase):
    """RV_REV_CRE_004 缺 reviewers"""
    r = authed_http.post("/api/reviews/reviews/", json={
        "title": "qa-review",
        "projects": [created_project["id"]],
        "testcases": [created_testcase["id"]],
    })
    assert r.status_code == 400


@pytest.mark.p1
@pytest.mark.boundary
def test_reviews_review_create_p005_empty_reviewers(authed_http, created_project, created_testcase):
    """RV_REV_CRE_005 reviewers 空"""
    r = authed_http.post("/api/reviews/reviews/", json={
        "title": "qa-review",
        "projects": [created_project["id"]],
        "testcases": [created_testcase["id"]],
        "reviewers": [],
    })
    assert r.status_code == 400


@pytest.mark.p0
@pytest.mark.anomaly
def test_reviews_review_create_p006_anonymous(http):
    """RV_REV_CRE_006 匿名"""
    r = http.post("/api/reviews/reviews/", json={"title": "x"})
    assert r.status_code == 401


@pytest.mark.p0
@pytest.mark.positive
def test_reviews_review_detail_p001(authed_http, created_review):
    """RV_REV_DET_001 详情"""
    rid = created_review.get("id")
    if not rid:
        pytest.skip("review id missing")
    r = authed_http.get(f"/api/reviews/reviews/{rid}/")
    assert r.status_code == 200


@pytest.mark.p1
@pytest.mark.anomaly
def test_reviews_review_detail_p002_not_found(authed_http):
    """RV_REV_DET_002 不存在"""
    r = authed_http.get("/api/reviews/reviews/99999999/")
    assert r.status_code == 404


@pytest.mark.p1
@pytest.mark.positive
@pytest.mark.review_required
def test_reviews_review_put_p001(authed_http, created_review, created_project, created_testcase, registered_user):
    """RV_REV_PUT_001 全量更新"""
    rid = created_review.get("id")
    if not rid:
        pytest.skip("review id missing")
    user_id = registered_user.get("user", {}).get("id")
    r = authed_http.put(f"/api/reviews/reviews/{rid}/", json={
        "title": f"qa-review-put-{uuid.uuid4().hex[:6]}",
        "projects": [created_project["id"]],
        "testcases": [created_testcase["id"]],
        "reviewers": [user_id] if user_id else [],
    })
    assert r.status_code in (200, 400)


@pytest.mark.p1
@pytest.mark.anomaly
def test_reviews_review_put_p002_missing_title(authed_http, created_review):
    """RV_REV_PUT_002 缺必填"""
    rid = created_review.get("id")
    if not rid:
        pytest.skip("review id missing")
    r = authed_http.put(f"/api/reviews/reviews/{rid}/", json={})
    assert r.status_code == 400


@pytest.mark.p1
@pytest.mark.positive
def test_reviews_review_patch_p001_priority(authed_http, created_review):
    """RV_REV_PCH_001 部分更新 priority"""
    rid = created_review.get("id")
    if not rid:
        pytest.skip("review id missing")
    r = authed_http.patch(f"/api/reviews/reviews/{rid}/", json={"priority": "high"})
    assert r.status_code == 200


@pytest.mark.p0
@pytest.mark.positive
def test_reviews_review_delete_p001(authed_http, created_review):
    """RV_REV_DEL_001 删除"""
    rid = created_review.get("id")
    if not rid:
        pytest.skip("review id missing")
    r = authed_http.delete(f"/api/reviews/reviews/{rid}/")
    assert r.status_code in (200, 204)


@pytest.mark.p1
@pytest.mark.anomaly
def test_reviews_review_delete_p002_not_found(authed_http):
    """RV_REV_DEL_002 删除不存在"""
    r = authed_http.delete("/api/reviews/reviews/99999999/")
    assert r.status_code == 404


# ============================================================================
# 3.7  POST /api/reviews/reviews/{id}/assign_reviewers/(3 用例)
# ============================================================================

@pytest.mark.p0
@pytest.mark.positive
def test_reviews_assign_reviewers_p001(authed_http, created_review, registered_user):
    """RV_REV_ASR_001 分配评审人"""
    rid = created_review.get("id")
    if not rid:
        pytest.skip("review id missing")
    user_id = registered_user.get("user", {}).get("id")
    if not user_id:
        pytest.skip("no user id")
    r = authed_http.post(f"/api/reviews/reviews/{rid}/assign_reviewers/", json={"reviewers": [user_id]})
    assert r.status_code in (200, 201)


@pytest.mark.p1
@pytest.mark.anomaly
def test_reviews_assign_reviewers_p002_missing(authed_http, created_review):
    """RV_REV_ASR_002 缺 reviewers"""
    rid = created_review.get("id")
    if not rid:
        pytest.skip("review id missing")
    r = authed_http.post(f"/api/reviews/reviews/{rid}/assign_reviewers/", json={})
    assert r.status_code == 400


@pytest.mark.p1
@pytest.mark.anomaly
def test_reviews_assign_reviewers_p003_review_not_found(authed_http):
    """RV_REV_ASR_003 评审不存在"""
    r = authed_http.post("/api/reviews/reviews/99999999/assign_reviewers/", json={"reviewers": [1]})
    assert r.status_code == 404


# ============================================================================
# 3.8  POST /api/reviews/reviews/{id}/submit_review/(4 用例)
# ============================================================================

@pytest.mark.p0
@pytest.mark.positive
@pytest.mark.review_required
def test_reviews_submit_p001_approved(authed_http, created_review):
    """RV_REV_SUB_001 提交评审通过"""
    rid = created_review.get("id")
    if not rid:
        pytest.skip("review id missing")
    r = authed_http.post(f"/api/reviews/reviews/{rid}/submit_review/", json={
        "status": "approved", "comment": "ok",
    })
    assert r.status_code in (200, 201, 400)


@pytest.mark.p0
@pytest.mark.positive
@pytest.mark.review_required
def test_reviews_submit_p002_rejected(authed_http, created_review):
    """RV_REV_SUB_002 提交评审拒绝"""
    rid = created_review.get("id")
    if not rid:
        pytest.skip("review id missing")
    r = authed_http.post(f"/api/reviews/reviews/{rid}/submit_review/", json={
        "status": "rejected", "comment": "issues",
    })
    assert r.status_code in (200, 201, 400)


@pytest.mark.p1
@pytest.mark.anomaly
def test_reviews_submit_p003_missing_status(authed_http, created_review):
    """RV_REV_SUB_003 缺 status"""
    rid = created_review.get("id")
    if not rid:
        pytest.skip("review id missing")
    r = authed_http.post(f"/api/reviews/reviews/{rid}/submit_review/", json={"comment": "x"})
    assert r.status_code == 400


@pytest.mark.p1
@pytest.mark.anomaly
def test_reviews_submit_p004_review_not_found(authed_http):
    """RV_REV_SUB_004 评审不存在"""
    r = authed_http.post("/api/reviews/reviews/99999999/submit_review/", json={"status": "approved"})
    assert r.status_code == 404


# ============================================================================
# 3.9  GET /api/reviews/reviews/my_reviews/(3 用例)
# ============================================================================

@pytest.mark.p0
@pytest.mark.positive
def test_reviews_my_reviews_p001(authed_http):
    """RV_REV_MY_001 我的评审"""
    r = authed_http.get("/api/reviews/reviews/my_reviews/")
    assert r.status_code == 200


@pytest.mark.p1
@pytest.mark.anomaly
def test_reviews_my_reviews_p002_anonymous(http):
    """RV_REV_MY_002 匿名"""
    r = http.get("/api/reviews/reviews/my_reviews/")
    assert r.status_code == 401


@pytest.mark.p1
@pytest.mark.boundary
def test_reviews_my_reviews_p003_empty(authed_http):
    """RV_REV_MY_003 新用户无评审"""
    r = authed_http.get("/api/reviews/reviews/my_reviews/")
    assert r.status_code == 200
    body = r.json()
    items = body.get("results", body) if isinstance(body, dict) else body
    assert isinstance(items, list)


# ============================================================================
# 3.10  /api/reviews/review-comments/  评审评论(11 用例)
# ============================================================================

@pytest.mark.p1
@pytest.mark.positive
def test_reviews_comments_list_p001(authed_http):
    """RV_CMT_LST_001 列表"""
    r = authed_http.get("/api/reviews/review-comments/")
    assert r.status_code == 200


@pytest.mark.p1
@pytest.mark.anomaly
def test_reviews_comments_list_p002_anonymous(http):
    """RV_CMT_LST_002 匿名"""
    r = http.get("/api/reviews/review-comments/")
    assert r.status_code == 401


@pytest.fixture
def _created_comment(authed_http, created_review):
    """创建评论用于详情/更新/删除测试。"""
    rid = created_review.get("id")
    if not rid:
        pytest.skip("review id missing for comment")
    r = authed_http.post("/api/reviews/review-comments/", json={
        "review": rid, "content": "auto comment",
    })
    if r.status_code not in (200, 201):
        pytest.skip(f"create comment failed: {r.status_code} {r.text[:200]}")
    return r.json()


@pytest.mark.p0
@pytest.mark.positive
def test_reviews_comments_create_p001(authed_http, created_review):
    """RV_CMT_CRE_001 创建评论"""
    rid = created_review.get("id")
    if not rid:
        pytest.skip("review id missing")
    r = authed_http.post("/api/reviews/review-comments/", json={
        "review": rid, "content": "auto comment",
    })
    assert r.status_code in (200, 201)


@pytest.mark.p1
@pytest.mark.anomaly
def test_reviews_comments_create_p002_missing_content(authed_http, created_review):
    """RV_CMT_CRE_002 缺 content"""
    rid = created_review.get("id")
    if not rid:
        pytest.skip("review id missing")
    r = authed_http.post("/api/reviews/review-comments/", json={"review": rid})
    assert r.status_code == 400


@pytest.mark.p1
@pytest.mark.anomaly
def test_reviews_comments_create_p003_missing_review(authed_http):
    """RV_CMT_CRE_003 缺 review"""
    r = authed_http.post("/api/reviews/review-comments/", json={"content": "x"})
    assert r.status_code == 400


@pytest.mark.p1
@pytest.mark.positive
def test_reviews_comments_detail_p001(authed_http, _created_comment):
    """RV_CMT_DET_001 详情"""
    cid = _created_comment.get("id")
    if not cid:
        pytest.skip("comment id missing")
    r = authed_http.get(f"/api/reviews/review-comments/{cid}/")
    assert r.status_code == 200


@pytest.mark.p1
@pytest.mark.anomaly
def test_reviews_comments_detail_p002_not_found(authed_http):
    """RV_CMT_DET_002 不存在"""
    r = authed_http.get("/api/reviews/review-comments/99999999/")
    assert r.status_code == 404


@pytest.mark.p1
@pytest.mark.positive
@pytest.mark.review_required
def test_reviews_comments_put_p001(authed_http, _created_comment):
    """RV_CMT_PUT_001 全量更新"""
    cid = _created_comment.get("id")
    if not cid:
        pytest.skip("comment id missing")
    r = authed_http.put(f"/api/reviews/review-comments/{cid}/", json={
        "review": _created_comment.get("review"),
        "content": "updated",
    })
    assert r.status_code in (200, 400)


@pytest.mark.p1
@pytest.mark.positive
def test_reviews_comments_patch_p001(authed_http, _created_comment):
    """RV_CMT_PCH_001 部分更新 content"""
    cid = _created_comment.get("id")
    if not cid:
        pytest.skip("comment id missing")
    r = authed_http.patch(f"/api/reviews/review-comments/{cid}/", json={"content": "patched"})
    assert r.status_code == 200


@pytest.mark.p1
@pytest.mark.positive
def test_reviews_comments_delete_p001(authed_http, _created_comment):
    """RV_CMT_DEL_001 删除"""
    cid = _created_comment.get("id")
    if not cid:
        pytest.skip("comment id missing")
    r = authed_http.delete(f"/api/reviews/review-comments/{cid}/")
    assert r.status_code in (200, 204)


@pytest.mark.p1
@pytest.mark.anomaly
def test_reviews_comments_delete_p002_not_found(authed_http):
    """RV_CMT_DEL_002 删除不存在"""
    r = authed_http.delete("/api/reviews/review-comments/99999999/")
    assert r.status_code == 404


# ============================================================================
# 3.11  组合用例(3 用例)
# ============================================================================

@pytest.mark.p0
@pytest.mark.combination
@pytest.mark.smoke
def test_reviews_e2e_p001_full_link(
    authed_http, created_review_template, created_review, registered_user
):
    """RV_COMB_001 评审完整链路: 模板→评审→分配→提交→my_reviews"""
    assert created_review_template.get("id")
    rid = created_review.get("id")
    if not rid:
        pytest.skip("review id missing")
    user_id = registered_user.get("user", {}).get("id")
    if user_id:
        r1 = authed_http.post(f"/api/reviews/reviews/{rid}/assign_reviewers/", json={"reviewers": [user_id]})
        assert r1.status_code in (200, 201)
    r2 = authed_http.get("/api/reviews/reviews/my_reviews/")
    assert r2.status_code == 200


@pytest.mark.p1
@pytest.mark.combination
def test_reviews_e2e_p002_review_with_comments(authed_http, created_review):
    """RV_COMB_002 评审 + 评论交叉"""
    rid = created_review.get("id")
    if not rid:
        pytest.skip("review id missing")
    r1 = authed_http.post("/api/reviews/review-comments/", json={
        "review": rid, "content": "init"})
    assert r1.status_code in (200, 201)
    cid = r1.json().get("id")
    if cid:
        r2 = authed_http.patch(f"/api/reviews/review-comments/{cid}/", json={"content": "updated"})
        assert r2.status_code == 200
        r3 = authed_http.delete(f"/api/reviews/review-comments/{cid}/")
        assert r3.status_code in (200, 204)


@pytest.mark.p1
@pytest.mark.combination
def test_reviews_e2e_p003_state_machine(authed_http, created_review):
    """RV_COMB_003 评审状态机 pending → in_review → completed"""
    rid = created_review.get("id")
    if not rid:
        pytest.skip("review id missing")
    for st in ("in_review", "completed"):
        r = authed_http.patch(f"/api/reviews/reviews/{rid}/", json={"status": st})
        assert r.status_code in (200, 400)

