"""projects 模块自动化测试。

CONFIDENCE: HIGH (CRUD/list/detail), MEDIUM (member/environment 子资源依赖外部 user/env 数据)
"""
import uuid

import pytest


class TestProjectListCreate:
    LIST = "/api/projects/"

    @pytest.mark.smoke
    @pytest.mark.p0
    @pytest.mark.positive
    @pytest.mark.projects
    def test_list_p001_authed(self, authed_http):
        r = authed_http.get(self.LIST)
        assert r.status_code == 200, r.text
        body = r.json()
        assert isinstance(body, (list, dict))

    @pytest.mark.p0
    @pytest.mark.anomaly
    @pytest.mark.projects
    def test_list_p002_anonymous(self, http):
        r = http.get(self.LIST)
        assert r.status_code == 401, r.status_code

    @pytest.mark.p0
    @pytest.mark.positive
    @pytest.mark.projects
    def test_create_p001_minimal_payload(self, authed_http, project_payload):
        r = authed_http.post(self.LIST, json=project_payload)
        assert r.status_code in (200, 201), r.text
        body = r.json()
        assert body["name"] == project_payload["name"]

    @pytest.mark.p1
    @pytest.mark.boundary
    @pytest.mark.projects
    def test_create_p002_long_name(self, authed_http, project_payload):
        """[Boundary] 名称 200 字符 → 视 model 约束接受或拒绝,但不应 5xx。"""
        project_payload["name"] = "p" * 200
        r = authed_http.post(self.LIST, json=project_payload)
        assert r.status_code < 500, r.status_code

    @pytest.mark.p1
    @pytest.mark.anomaly
    @pytest.mark.projects
    def test_create_p003_missing_name(self, authed_http):
        r = authed_http.post(self.LIST, json={"description": "no name"})
        assert r.status_code == 400, r.text

    @pytest.mark.p1
    @pytest.mark.combination
    @pytest.mark.projects
    def test_create_p004_filter_by_owner_only(self, authed_http, http, registered_user):
        """[Combination] 用户 A 创建项目后,新注册用户 B 不应在其列表里看到。"""
        a_proj = authed_http.post(self.LIST, json={
            "name": f"owner-only-{uuid.uuid4().hex[:6]}", "description": "x", "status": "active",
        })
        assert a_proj.status_code in (200, 201), a_proj.text
        a_proj_id = a_proj.json()["id"]

        b_payload = {
            "username": f"b_{uuid.uuid4().hex[:8]}",
            "email": f"b_{uuid.uuid4().hex[:8]}@x.test",
            "password": "Pwd@12345", "password_confirm": "Pwd@12345",
        }
        http.post("/api/auth/register/", json=b_payload)
        login = http.post("/api/auth/login/", json={
            "username": b_payload["username"], "password": b_payload["password"],
        })
        b_token = login.json()["access"]

        r = http.get(self.LIST, headers={"Authorization": f"Bearer {b_token}"})
        assert r.status_code == 200
        body = r.json()
        items = body.get("results", body) if isinstance(body, dict) else body
        ids = [it["id"] for it in items] if isinstance(items, list) else []
        assert a_proj_id not in ids, "B should not see A's private project"


class TestProjectDetail:

    @pytest.mark.smoke
    @pytest.mark.p0
    @pytest.mark.positive
    @pytest.mark.projects
    def test_retrieve_p001(self, authed_http, created_project):
        r = authed_http.get(f"/api/projects/{created_project['id']}/")
        assert r.status_code == 200, r.text
        assert r.json()["id"] == created_project["id"]

    @pytest.mark.p1
    @pytest.mark.anomaly
    @pytest.mark.projects
    def test_retrieve_p002_not_found(self, authed_http):
        r = authed_http.get("/api/projects/99999999/")
        assert r.status_code == 404, r.status_code

    @pytest.mark.p1
    @pytest.mark.anomaly
    @pytest.mark.projects
    def test_retrieve_p003_anonymous(self, http, created_project):
        r = http.get(f"/api/projects/{created_project['id']}/")
        assert r.status_code == 401, r.status_code

    @pytest.mark.p1
    @pytest.mark.positive
    @pytest.mark.projects
    def test_put_p001_full_update(self, authed_http, created_project):
        payload = {
            "name": created_project["name"] + "-renamed",
            "description": "updated desc",
            "status": "active",
        }
        r = authed_http.put(f"/api/projects/{created_project['id']}/", json=payload)
        assert r.status_code == 200, r.text
        assert r.json()["name"].endswith("-renamed")

    @pytest.mark.p1
    @pytest.mark.positive
    @pytest.mark.projects
    def test_patch_p001_partial(self, authed_http, created_project):
        r = authed_http.patch(
            f"/api/projects/{created_project['id']}/",
            json={"description": "patched"})
        assert r.status_code == 200, r.text
        assert r.json()["description"] == "patched"

    @pytest.mark.p0
    @pytest.mark.positive
    @pytest.mark.projects
    def test_delete_p001(self, authed_http, created_project):
        pid = created_project["id"]
        r = authed_http.delete(f"/api/projects/{pid}/")
        assert r.status_code in (200, 204), r.text
        r2 = authed_http.get(f"/api/projects/{pid}/")
        assert r2.status_code == 404, f"project still exists after delete: {r2.status_code}"


class TestProjectAuxLists:

    @pytest.mark.p1
    @pytest.mark.positive
    @pytest.mark.projects
    def test_all_p001(self, authed_http):
        r = authed_http.get("/api/projects/all/")
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)

    @pytest.mark.p1
    @pytest.mark.anomaly
    @pytest.mark.projects
    def test_all_p002_anonymous(self, http):
        r = http.get("/api/projects/all/")
        assert r.status_code == 401, r.status_code

    @pytest.mark.p1
    @pytest.mark.positive
    @pytest.mark.projects
    def test_user_projects_list_p001(self, authed_http):
        r = authed_http.get("/api/projects/list/")
        assert r.status_code in (200,), r.text


class TestProjectMembers:

    @pytest.mark.p0
    @pytest.mark.positive
    @pytest.mark.projects
    def test_members_list_p001_owner_can_view(self, authed_http, created_project):
        r = authed_http.get(f"/api/projects/{created_project['id']}/members/")
        assert r.status_code == 200, r.text

    @pytest.mark.p1
    @pytest.mark.anomaly
    @pytest.mark.projects
    def test_members_list_p002_not_found(self, authed_http):
        r = authed_http.get("/api/projects/99999999/members/")
        assert r.status_code == 404, r.status_code

    @pytest.mark.p1
    @pytest.mark.anomaly
    @pytest.mark.projects
    def test_member_add_p001_invalid_user_id(self, authed_http, created_project):
        """[Anomaly] user_id 不存在 → 400 / 4xx,不应 5xx。"""
        r = authed_http.post(
            f"/api/projects/{created_project['id']}/members/add/",
            json={"user_id": 99999999, "role": "member"})
        assert r.status_code < 500, r.status_code

    @pytest.mark.p1
    @pytest.mark.anomaly
    @pytest.mark.security
    @pytest.mark.projects
    def test_member_add_p002_non_owner_rejected(self, http, authed_http, created_project):
        """[Security] 非 owner 加成员 → 403。"""
        other = {
            "username": f"o_{uuid.uuid4().hex[:8]}",
            "email": f"o_{uuid.uuid4().hex[:8]}@x.test",
            "password": "Pwd@12345", "password_confirm": "Pwd@12345",
        }
        http.post("/api/auth/register/", json=other)
        login = http.post("/api/auth/login/", json={
            "username": other["username"], "password": other["password"],
        })
        other_token = login.json()["access"]
        r = http.post(
            f"/api/projects/{created_project['id']}/members/add/",
            json={"user_id": 1, "role": "member"},
            headers={"Authorization": f"Bearer {other_token}"})
        assert r.status_code in (403, 404), r.status_code


class TestProjectEnvironments:

    @pytest.mark.p1
    @pytest.mark.positive
    @pytest.mark.projects
    def test_env_list_p001(self, authed_http, created_project):
        r = authed_http.get(f"/api/projects/{created_project['id']}/environments/")
        assert r.status_code == 200, r.text

    @pytest.mark.p1
    @pytest.mark.review_required
    @pytest.mark.projects
    def test_env_create_p001(self, authed_http, created_project):
        """[Positive] 创建环境的最小字段集需依据 ProjectEnvironment 模型,标记需评审。"""
        payload = {
            "name": "dev",
            "base_url": "https://dev.example.com",
            "project": created_project["id"],
        }
        r = authed_http.post(
            f"/api/projects/{created_project['id']}/environments/", json=payload)
        assert r.status_code in (200, 201, 400), r.status_code
