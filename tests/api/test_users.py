"""users 模块测试。

注意: backend/urls.py 同时把 apps.users.urls 挂载到 /api/auth/ 与 /api/users/,
两组路径行为完全等价。本文件仅做"别名一致性"验证,避免与 test_auth.py 大量重复。

CONFIDENCE: HIGH
"""
import pytest


PREFIXES = ["/api/auth", "/api/users"]


class TestUsersAlias:

    @pytest.mark.smoke
    @pytest.mark.p1
    @pytest.mark.combination
    @pytest.mark.users
    @pytest.mark.parametrize("prefix", PREFIXES)
    def test_alias_p001_login_works_on_both(self, http, registered_user, prefix):
        """[Combination] /api/auth/login/ 与 /api/users/login/ 行为一致。"""
        r = http.post(f"{prefix}/login/", json={
            "username": registered_user["username"],
            "password": registered_user["password"],
        })
        assert r.status_code == 200, f"{prefix}: {r.text}"
        body = r.json()
        assert "access" in body and "refresh" in body

    @pytest.mark.p1
    @pytest.mark.positive
    @pytest.mark.users
    @pytest.mark.parametrize("prefix", PREFIXES)
    def test_alias_p002_me_consistent(self, authed_http, registered_user, prefix):
        r = authed_http.get(f"{prefix}/me/")
        assert r.status_code == 200, f"{prefix}: {r.text}"
        assert r.json()["username"] == registered_user["username"]

    @pytest.mark.p1
    @pytest.mark.anomaly
    @pytest.mark.users
    @pytest.mark.parametrize("prefix", PREFIXES)
    def test_alias_p003_anonymous_me_rejected(self, http, prefix):
        r = http.get(f"{prefix}/me/")
        assert r.status_code == 401, f"{prefix}: {r.status_code}"

    @pytest.mark.p1
    @pytest.mark.combination
    @pytest.mark.users
    def test_alias_p004_register_then_login_via_alias(self, http, random_user_payload):
        """[Combination] /api/users/register/ 注册 → /api/auth/login/ 登录,跨别名链路成立。"""
        r1 = http.post("/api/users/register/", json=random_user_payload)
        assert r1.status_code == 201, r1.text

        r2 = http.post("/api/auth/login/", json={
            "username": random_user_payload["username"],
            "password": random_user_payload["password"],
        })
        assert r2.status_code == 200, r2.text
