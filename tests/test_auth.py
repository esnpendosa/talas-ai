"""
TALAS AI — Test Authentication & RBAC
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


# ------------------------------------------------------------------ #
# Fixture: seeded client (fresh DB per test via rollback)
# ------------------------------------------------------------------ #

@pytest.fixture
async def seeded_client(client, db_session):
    """Client dengan data auth yang sudah di-seed."""
    from app.models.user import User, Role, Permission, UserRole, RolePermission
    from app.services.security.hashing import hash_password
    import uuid as _uuid

    suffix = _uuid.uuid4().hex[:6]

    # Role analis
    role = Role(name=f"analis_{suffix}", display_name="Analis Hukum")
    db_session.add(role)
    await db_session.flush()

    perm = Permission(
        name=f"regulations:read:{suffix}",
        resource="regulations",
        action="read",
        description="Lihat regulasi",
    )
    db_session.add(perm)
    await db_session.flush()
    db_session.add(RolePermission(role_id=role.id, permission_id=perm.id))

    # User biasa
    user = User(
        username=f"testuser_{suffix}",
        email=f"test_{suffix}@talas.local",
        full_name="Test User",
        hashed_password=hash_password("TestPass@123"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(UserRole(user_id=user.id, role_id=role.id))

    # Role admin
    admin_role = Role(name=f"admin_{suffix}", display_name="Admin")
    db_session.add(admin_role)
    await db_session.flush()

    admin = User(
        username=f"admin_{suffix}",
        email=f"admin_{suffix}@talas.local",
        full_name="Administrator",
        hashed_password=hash_password("AdminPass@123"),
        is_active=True,
        is_superuser=True,
    )
    db_session.add(admin)
    await db_session.flush()
    db_session.add(UserRole(user_id=admin.id, role_id=admin_role.id))

    # Role untuk user baru yang akan dibuat di test
    new_role = Role(name=f"opd_{suffix}", display_name="OPD")
    db_session.add(new_role)

    await db_session.commit()

    return {
        "client": client,
        "username": f"testuser_{suffix}",
        "admin_username": f"admin_{suffix}",
        "new_role": f"opd_{suffix}",
        "suffix": suffix,
    }


# ------------------------------------------------------------------ #
# Login Tests
# ------------------------------------------------------------------ #

class TestLogin:
    @pytest.mark.asyncio
    async def test_login_success(self, seeded_client):
        c = seeded_client["client"]
        response = await c.post("/api/auth/login", json={
            "username": seeded_client["username"],
            "password": "TestPass@123",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, seeded_client):
        c = seeded_client["client"]
        response = await c.post("/api/auth/login", json={
            "username": seeded_client["username"],
            "password": "wrongpassword",
        })
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_unknown_user(self, client):
        response = await client.post("/api/auth/login", json={
            "username": "useryangtidakada_xyz",
            "password": "anypassword",
        })
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_response_no_sensitive_data(self, seeded_client):
        """Response login tidak boleh mengandung hash password."""
        c = seeded_client["client"]
        response = await c.post("/api/auth/login", json={
            "username": seeded_client["username"],
            "password": "TestPass@123",
        })
        assert response.status_code == 200
        body = response.text
        assert "argon2" not in body.lower()
        assert "hashed" not in body.lower()
        assert "access_token" in body


# ------------------------------------------------------------------ #
# Get Me Tests
# ------------------------------------------------------------------ #

class TestGetMe:
    @pytest.mark.asyncio
    async def test_get_me_authenticated(self, seeded_client):
        c = seeded_client["client"]
        login = await c.post("/api/auth/login", json={
            "username": seeded_client["username"],
            "password": "TestPass@123",
        })
        token = login.json()["access_token"]
        response = await c.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == seeded_client["username"]
        assert "hashed_password" not in data
        assert "roles" in data

    @pytest.mark.asyncio
    async def test_get_me_unauthenticated(self, client):
        response = await client.get("/api/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_invalid_token(self, client):
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer token-palsu-tidak-valid"},
        )
        assert response.status_code == 401


# ------------------------------------------------------------------ #
# Change Password Tests
# ------------------------------------------------------------------ #

class TestChangePassword:
    @pytest.mark.asyncio
    async def test_change_password_success(self, seeded_client):
        c = seeded_client["client"]
        login = await c.post("/api/auth/login", json={
            "username": seeded_client["username"],
            "password": "TestPass@123",
        })
        token = login.json()["access_token"]
        response = await c.post(
            "/api/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={"current_password": "TestPass@123", "new_password": "NewPass@456"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, seeded_client):
        c = seeded_client["client"]
        login = await c.post("/api/auth/login", json={
            "username": seeded_client["username"],
            "password": "TestPass@123",
        })
        token = login.json()["access_token"]
        response = await c.post(
            "/api/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={"current_password": "salah", "new_password": "NewPass@456"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_change_password_too_short(self, seeded_client):
        c = seeded_client["client"]
        login = await c.post("/api/auth/login", json={
            "username": seeded_client["username"],
            "password": "TestPass@123",
        })
        token = login.json()["access_token"]
        response = await c.post(
            "/api/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={"current_password": "TestPass@123", "new_password": "short"},
        )
        assert response.status_code == 422


# ------------------------------------------------------------------ #
# Logout Tests
# ------------------------------------------------------------------ #

class TestLogout:
    @pytest.mark.asyncio
    async def test_logout_success(self, seeded_client):
        c = seeded_client["client"]
        login = await c.post("/api/auth/login", json={
            "username": seeded_client["username"],
            "password": "TestPass@123",
        })
        token = login.json()["access_token"]
        response = await c.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_logout_unauthenticated(self, client):
        response = await client.post("/api/auth/logout")
        assert response.status_code == 401


# ------------------------------------------------------------------ #
# RBAC Tests
# ------------------------------------------------------------------ #

class TestRBAC:
    @pytest.mark.asyncio
    async def test_admin_can_list_users(self, seeded_client):
        c = seeded_client["client"]
        login = await c.post("/api/auth/login", json={
            "username": seeded_client["admin_username"],
            "password": "AdminPass@123",
        })
        token = login.json()["access_token"]
        response = await c.get(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_regular_user_cannot_list_users(self, seeded_client):
        c = seeded_client["client"]
        login = await c.post("/api/auth/login", json={
            "username": seeded_client["username"],
            "password": "TestPass@123",
        })
        token = login.json()["access_token"]
        response = await c.get(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_can_create_user(self, seeded_client):
        c = seeded_client["client"]
        login = await c.post("/api/auth/login", json={
            "username": seeded_client["admin_username"],
            "password": "AdminPass@123",
        })
        token = login.json()["access_token"]
        suffix = seeded_client["suffix"]
        response = await c.post(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "username": f"newuser_{suffix}",
                "email": f"newuser_{suffix}@talas.local",
                "full_name": "New User",
                "password": "NewUser@123",
                "role": seeded_client["new_role"],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == f"newuser_{suffix}"
        assert "hashed_password" not in data

    @pytest.mark.asyncio
    async def test_unauthenticated_cannot_access_admin(self, client):
        response = await client.get("/api/admin/users")
        assert response.status_code == 401
