"""auth 模块 13 个接口的自动化测试 (六维场景覆盖)。

接口清单与覆盖矩阵详见同目录 testcases.md。

CONFIDENCE: HIGH — 输入来自 swagger + 后端代码精确解析,断言直接对照 view 实现。
"""
import uuid

import pytest
import requests


# ======================================================================
# 1. POST /api/auth/register/  注册
# ======================================================================
class TestAuthRegister:
    ENDPOINT = "/api/auth/register/"

    @pytest.mark.smoke
    @pytest.mark.p0
    @pytest.mark.positive
    @pytest.mark.auth
    def test_register_p001_success_with_valid_payload(self, http, random_user_payload):
        """[Positive] 完整合法字段 → 201,返回 user 与 token。"""
        r = http.post(self.ENDPOINT, json=random_user_payload)
        assert r.status_code == 201, r.text
        body = r.json()
        assert "user" in body and "token" in body
        assert body["user"]["username"] == random_user_payload["username"]
        assert body["user"]["email"] == random_user_payload["email"]
        assert "password" not in body["user"]

    @pytest.mark.p1
    @pytest.mark.boundary
    @pytest.mark.auth
    def test_register_p002_password_min_length_6(self, http, random_user_payload):
        """[Boundary] 密码恰好 6 位 → 注册成功。"""
        random_user_payload["password"] = "abc123"
        random_user_payload["password_confirm"] = "abc123"
        r = http.post(self.ENDPOINT, json=random_user_payload)
        assert r.status_code == 201, r.text

    @pytest.mark.p1
    @pytest.mark.boundary
    @pytest.mark.anomaly
    @pytest.mark.auth
    def test_register_p003_password_below_min_length(self, http, random_user_payload):
        """[Boundary/Anomaly] 密码 5 位 → 400 校验失败。"""
        random_user_payload["password"] = "abcde"
        random_user_payload["password_confirm"] = "abcde"
        r = http.post(self.ENDPOINT, json=random_user_payload)
        assert r.status_code == 400, r.text

    @pytest.mark.p1
    @pytest.mark.anomaly
    @pytest.mark.auth
    def test_register_p004_password_mismatch(self, http, random_user_payload):
        """[Anomaly] 密码与 confirm 不一致 → 400 '密码不一致'。"""
        random_user_payload["password_confirm"] = "different_pwd"
        r = http.post(self.ENDPOINT, json=random_user_payload)
        assert r.status_code == 400, r.text

    @pytest.mark.p0
    @pytest.mark.anomaly
    @pytest.mark.auth
    def test_register_p005_duplicate_username(self, http, registered_user, random_user_payload):
        """[Anomaly] 用户名已存在 → 400。"""
        random_user_payload["username"] = registered_user["username"]
        r = http.post(self.ENDPOINT, json=random_user_payload)
        assert r.status_code == 400, r.text

    @pytest.mark.p1
    @pytest.mark.anomaly
    @pytest.mark.auth
    @pytest.mark.parametrize("missing_field", ["username", "password", "password_confirm"])
    def test_register_p006_missing_required_field(self, http, random_user_payload, missing_field):
        """[Anomaly] 必填字段缺失 → 400。"""
        random_user_payload.pop(missing_field)
        r = http.post(self.ENDPOINT, json=random_user_payload)
        assert r.status_code == 400, r.text

    @pytest.mark.p2
    @pytest.mark.security
    @pytest.mark.auth
    @pytest.mark.parametrize("malicious", [
        "admin' OR '1'='1",
        "<script>alert(1)</script>",
        "test;DROP TABLE users;",
    ])
    def test_register_p007_security_payload_in_username(self, http, random_user_payload, malicious):
        """[Security] 恶意字符串作为 username → 拒绝或安全转义,绝不返回 5xx。"""
        random_user_payload["username"] = malicious
        r = http.post(self.ENDPOINT, json=random_user_payload)
        assert r.status_code < 500, f"server crashed on malicious input: {r.status_code}"


# ======================================================================
# 2. POST /api/auth/login/  登录
# ======================================================================
class TestAuthLogin:
    ENDPOINT = "/api/auth/login/"

    @pytest.mark.smoke
    @pytest.mark.p0
    @pytest.mark.positive
    @pytest.mark.auth
    def test_login_p001_success(self, http, registered_user):
        """[Positive] 合法账密 → 200,返回 access/refresh/expires_in。"""
        r = http.post(self.ENDPOINT, json={
            "username": registered_user["username"],
            "password": registered_user["password"],
        })
        assert r.status_code == 200, r.text
        body = r.json()
        for key in ("access", "refresh", "user", "access_expires_in", "refresh_expires_in"):
            assert key in body, f"missing field {key}"
        assert body["user"]["username"] == registered_user["username"]
        assert isinstance(body["access_expires_in"], int) and body["access_expires_in"] > 0

    @pytest.mark.p0
    @pytest.mark.anomaly
    @pytest.mark.auth
    def test_login_p002_wrong_password(self, http, registered_user):
        """[Anomaly] 密码错误 → 400 含 error 字段。"""
        r = http.post(self.ENDPOINT, json={
            "username": registered_user["username"],
            "password": "wrong_password_999",
        })
        assert r.status_code == 400, r.text
        assert "error" in r.json()

    @pytest.mark.p1
    @pytest.mark.anomaly
    @pytest.mark.auth
    def test_login_p003_nonexistent_user(self, http):
        """[Anomaly] 用户名不存在 → 400。"""
        r = http.post(self.ENDPOINT, json={
            "username": f"ghost_{uuid.uuid4().hex[:8]}",
            "password": "anything12345",
        })
        assert r.status_code == 400, r.text

    @pytest.mark.p1
    @pytest.mark.boundary
    @pytest.mark.anomaly
    @pytest.mark.auth
    @pytest.mark.parametrize("payload", [
        {},
        {"username": "", "password": ""},
        {"username": "x"},
        {"password": "x"},
    ])
    def test_login_p004_empty_or_partial_fields(self, http, payload):
        """[Boundary/Anomaly] 字段缺失或为空 → 400。"""
        r = http.post(self.ENDPOINT, json=payload)
        assert r.status_code == 400, r.text

    @pytest.mark.p2
    @pytest.mark.security
    @pytest.mark.auth
    def test_login_p005_sql_injection_attempt(self, http):
        """[Security] SQL 注入字符 → 不返回 5xx,不应绕过认证。"""
        r = http.post(self.ENDPOINT, json={
            "username": "' OR 1=1 --",
            "password": "anything",
        })
        assert r.status_code in (400, 401), r.status_code
        assert "access" not in r.json()


# ======================================================================
# 3. POST /api/auth/logout/  登出
# ======================================================================
class TestAuthLogout:
    ENDPOINT = "/api/auth/logout/"

    @pytest.mark.p0
    @pytest.mark.positive
    @pytest.mark.auth
    def test_logout_p001_with_refresh_token(self, authed_http, login_tokens):
        """[Positive] 携带 refresh → 200,refresh 进入黑名单。"""
        r = authed_http.post(self.ENDPOINT, json={"refresh": login_tokens["refresh"]})
        assert r.status_code == 200, r.text
        assert "message" in r.json()

    @pytest.mark.p1
    @pytest.mark.anomaly
    @pytest.mark.auth
    def test_logout_p002_without_refresh(self, authed_http):
        """[Anomaly/Boundary] 不携带 refresh → 仍 200 (按当前实现宽容处理)。"""
        r = authed_http.post(self.ENDPOINT, json={})
        assert r.status_code == 200, r.text

    @pytest.mark.p1
    @pytest.mark.combination
    @pytest.mark.auth
    def test_logout_p003_blacklisted_refresh_cannot_refresh(self, authed_http, http, login_tokens):
        """[Combination] logout 后用旧 refresh 刷新 token → 应被拒绝。"""
        authed_http.post(self.ENDPOINT, json={"refresh": login_tokens["refresh"]})
        r = http.post("/api/auth/token/refresh/", json={"refresh": login_tokens["refresh"]})
        assert r.status_code in (400, 401), f"blacklisted token still accepted: {r.status_code}"


# ======================================================================
# 4. GET /api/auth/me/  当前用户信息
# ======================================================================
class TestAuthMe:
    ENDPOINT = "/api/auth/me/"

    @pytest.mark.smoke
    @pytest.mark.p0
    @pytest.mark.positive
    @pytest.mark.auth
    def test_me_p001_authed_returns_user(self, authed_http, registered_user):
        r = authed_http.get(self.ENDPOINT)
        assert r.status_code == 200, r.text
        assert r.json()["username"] == registered_user["username"]

    @pytest.mark.p0
    @pytest.mark.anomaly
    @pytest.mark.auth
    def test_me_p002_anonymous_rejected(self, http):
        r = http.get(self.ENDPOINT)
        assert r.status_code == 401, r.text

    @pytest.mark.p2
    @pytest.mark.security
    @pytest.mark.auth
    def test_me_p003_tampered_token(self, http, login_tokens, base_url):
        bad = login_tokens["access"][:-4] + "AAAA"
        r = requests.get(f"{base_url}{self.ENDPOINT}",
                         headers={"Authorization": f"Bearer {bad}"}, timeout=10)
        assert r.status_code == 401, r.status_code


# ======================================================================
# 5. GET /api/auth/profile/  用户资料
# ======================================================================
class TestAuthProfile:
    ENDPOINT = "/api/auth/profile/"

    @pytest.mark.p1
    @pytest.mark.positive
    @pytest.mark.auth
    def test_profile_p001_authed(self, authed_http, registered_user):
        r = authed_http.get(self.ENDPOINT)
        assert r.status_code == 200, r.text
        assert r.json()["username"] == registered_user["username"]

    @pytest.mark.p1
    @pytest.mark.anomaly
    @pytest.mark.auth
    def test_profile_p002_anonymous(self, http):
        r = http.get(self.ENDPOINT)
        assert r.status_code == 401, r.text


# ======================================================================
# 6. POST /api/auth/change-password/  修改密码
# ======================================================================
class TestAuthChangePassword:
    ENDPOINT = "/api/auth/change-password/"

    @pytest.mark.p0
    @pytest.mark.positive
    @pytest.mark.auth
    def test_change_pwd_p001_success(self, authed_http, registered_user):
        new_pwd = "NewPwd@9876"
        r = authed_http.post(self.ENDPOINT, json={
            "current_password": registered_user["password"],
            "new_password": new_pwd,
        })
        assert r.status_code == 200, r.text
        assert "message" in r.json()

    @pytest.mark.p1
    @pytest.mark.boundary
    @pytest.mark.auth
    def test_change_pwd_p002_new_password_below_min(self, authed_http, registered_user):
        r = authed_http.post(self.ENDPOINT, json={
            "current_password": registered_user["password"],
            "new_password": "abcde",
        })
        assert r.status_code == 400, r.text
        assert "6" in r.json().get("error", "")

    @pytest.mark.p1
    @pytest.mark.anomaly
    @pytest.mark.auth
    def test_change_pwd_p003_wrong_current(self, authed_http):
        r = authed_http.post(self.ENDPOINT, json={
            "current_password": "definitely_wrong",
            "new_password": "GoodPwd@1234",
        })
        assert r.status_code == 400, r.text

    @pytest.mark.p1
    @pytest.mark.anomaly
    @pytest.mark.auth
    def test_change_pwd_p004_same_as_current(self, authed_http, registered_user):
        r = authed_http.post(self.ENDPOINT, json={
            "current_password": registered_user["password"],
            "new_password": registered_user["password"],
        })
        assert r.status_code == 400, r.text

    @pytest.mark.p1
    @pytest.mark.anomaly
    @pytest.mark.auth
    @pytest.mark.parametrize("payload", [
        {"current_password": "", "new_password": ""},
        {"new_password": "GoodPwd@1234"},
        {"current_password": "x"},
    ])
    def test_change_pwd_p005_missing_fields(self, authed_http, payload):
        r = authed_http.post(self.ENDPOINT, json=payload)
        assert r.status_code == 400, r.text

    @pytest.mark.p1
    @pytest.mark.anomaly
    @pytest.mark.auth
    def test_change_pwd_p006_anonymous(self, http):
        r = http.post(self.ENDPOINT, json={
            "current_password": "x", "new_password": "GoodPwd@1234",
        })
        assert r.status_code == 401, r.status_code

    @pytest.mark.p0
    @pytest.mark.combination
    @pytest.mark.auth
    def test_change_pwd_p007_login_with_new_password(self, authed_http, http, registered_user):
        """[Combination] 改密成功后,旧密码失效、新密码可登录。"""
        new_pwd = "NewPwd@9876"
        r = authed_http.post(self.ENDPOINT, json={
            "current_password": registered_user["password"],
            "new_password": new_pwd,
        })
        assert r.status_code == 200, r.text

        r_old = http.post("/api/auth/login/", json={
            "username": registered_user["username"], "password": registered_user["password"],
        })
        assert r_old.status_code == 400, "old password still valid after change"

        r_new = http.post("/api/auth/login/", json={
            "username": registered_user["username"], "password": new_pwd,
        })
        assert r_new.status_code == 200, r_new.text


# ======================================================================
# 7. POST /api/auth/token/refresh/  刷新 token
# ======================================================================
class TestAuthTokenRefresh:
    ENDPOINT = "/api/auth/token/refresh/"

    @pytest.mark.p0
    @pytest.mark.positive
    @pytest.mark.auth
    def test_refresh_p001_success(self, http, login_tokens):
        r = http.post(self.ENDPOINT, json={"refresh": login_tokens["refresh"]})
        assert r.status_code == 200, r.text
        body = r.json()
        assert "access" in body and "access_expires_in" in body

    @pytest.mark.p1
    @pytest.mark.anomaly
    @pytest.mark.auth
    def test_refresh_p002_missing_refresh(self, http):
        r = http.post(self.ENDPOINT, json={})
        assert r.status_code == 400, r.text
        assert "refresh" in r.json().get("error", "").lower()

    @pytest.mark.p1
    @pytest.mark.anomaly
    @pytest.mark.auth
    def test_refresh_p003_invalid_refresh(self, http):
        r = http.post(self.ENDPOINT, json={"refresh": "this.is.not.a.valid.token"})
        assert r.status_code == 401, r.text


# ======================================================================
# 8-13. /api/auth/users[/{id}/]  用户 CRUD
# ======================================================================
class TestAuthUsersCRUD:
    LIST = "/api/auth/users/"

    @pytest.mark.p0
    @pytest.mark.positive
    @pytest.mark.auth
    def test_users_list_p001(self, authed_http):
        r = authed_http.get(self.LIST)
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), (list, dict))

    @pytest.mark.p1
    @pytest.mark.anomaly
    @pytest.mark.auth
    def test_users_list_p002_anonymous(self, http):
        r = http.get(self.LIST)
        assert r.status_code == 401, r.status_code

    @pytest.mark.p1
    @pytest.mark.review_required
    @pytest.mark.auth
    def test_users_create_p001_via_user_serializer(self, authed_http):
        """[Positive] POST /users/ — UserSerializer 不含 password 字段,
        实际可创建性取决于 User model required 字段的默认值,需评审。"""
        payload = {
            "username": f"uc_{uuid.uuid4().hex[:6]}",
            "email": f"uc_{uuid.uuid4().hex[:6]}@x.test",
        }
        r = authed_http.post(self.LIST, json=payload)
        assert r.status_code in (201, 400), f"unexpected: {r.status_code} {r.text}"

    @pytest.mark.p0
    @pytest.mark.positive
    @pytest.mark.auth
    def test_users_retrieve_p001(self, authed_http, registered_user):
        uid = registered_user["user"]["id"]
        r = authed_http.get(f"{self.LIST}{uid}/")
        assert r.status_code == 200, r.text
        assert r.json()["id"] == uid

    @pytest.mark.p1
    @pytest.mark.anomaly
    @pytest.mark.auth
    def test_users_retrieve_p002_not_found(self, authed_http):
        r = authed_http.get(f"{self.LIST}99999999/")
        assert r.status_code == 404, r.status_code

    @pytest.mark.p1
    @pytest.mark.positive
    @pytest.mark.auth
    def test_users_put_update_p001(self, authed_http, registered_user):
        uid = registered_user["user"]["id"]
        payload = {
            "username": registered_user["username"],
            "email": registered_user["email"],
            "first_name": "Updated",
            "last_name": "Name",
            "phone": "13800000000",
            "department": "QA",
            "position": "lead",
            "is_active": True,
        }
        r = authed_http.put(f"{self.LIST}{uid}/", json=payload)
        assert r.status_code == 200, r.text
        assert r.json()["first_name"] == "Updated"

    @pytest.mark.p1
    @pytest.mark.positive
    @pytest.mark.auth
    def test_users_patch_update_p001(self, authed_http, registered_user):
        uid = registered_user["user"]["id"]
        r = authed_http.patch(f"{self.LIST}{uid}/", json={"department": "Patched"})
        assert r.status_code == 200, r.text
        assert r.json()["department"] == "Patched"

    @pytest.mark.p0
    @pytest.mark.positive
    @pytest.mark.auth
    def test_users_delete_p001(self, authed_http, registered_user):
        uid = registered_user["user"]["id"]
        r = authed_http.delete(f"{self.LIST}{uid}/")
        assert r.status_code in (200, 204), r.text
        r2 = authed_http.get(f"{self.LIST}{uid}/")
        assert r2.status_code in (401, 404), f"user still readable: {r2.status_code}"

    @pytest.mark.p1
    @pytest.mark.anomaly
    @pytest.mark.auth
    def test_users_delete_p002_not_found(self, authed_http):
        r = authed_http.delete(f"{self.LIST}99999999/")
        assert r.status_code == 404, r.status_code
