"""
TALAS AI — Test Regulatory Library API
"""
from __future__ import annotations
import pytest
import uuid as _uuid


async def _make_analis(client, test_engine):
    """Buat user analis langsung via engine yang dipakai client."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from app.models.user import User, Role, Permission, UserRole, RolePermission
    from app.services.security.hashing import hash_password

    suffix = _uuid.uuid4().hex[:6]
    factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)

    async with factory() as session:
        role = Role(name=f"analis_{suffix}", display_name="Analis")
        session.add(role)
        await session.flush()

        for resource, action in [
            ("regulations", "read"), ("regulations", "write"), ("regulations", "delete")
        ]:
            perm = Permission(
                name=f"{resource}:{action}:{suffix}",  # name unik per test
                resource=resource,
                action=action,
            )
            session.add(perm)
            await session.flush()
            session.add(RolePermission(role_id=role.id, permission_id=perm.id))

        user = User(
            username=f"analis_{suffix}",
            email=f"analis_{suffix}@talas.local",
            full_name="Analis Hukum",
            hashed_password=hash_password("Pass@123"),
            is_active=True,
        )
        session.add(user)
        await session.flush()
        session.add(UserRole(user_id=user.id, role_id=role.id))
        await session.commit()

    login = await client.post("/api/auth/login", json={
        "username": f"analis_{suffix}", "password": "Pass@123"
    })
    token = login.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture
async def auth_client(client, test_engine):
    return await _make_analis(client, test_engine)


class TestRegulationCRUD:
    @pytest.mark.asyncio
    async def test_create_regulation(self, auth_client):
        response = await auth_client.post("/api/regulations", json={
            "jenis": "Perbup", "nomor": "1", "tahun": 2026,
            "judul": "Peraturan Bupati Test", "status": "BERLAKU",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["jenis"] == "Perbup"
        assert data["level"] == 8
        assert "uuid" in data

    @pytest.mark.asyncio
    async def test_list_regulations(self, auth_client):
        # Buat dua regulasi
        await auth_client.post("/api/regulations", json={
            "jenis": "UU", "nomor": "23", "tahun": 2014,
            "judul": "Pemerintahan Daerah", "status": "BERLAKU",
        })
        await auth_client.post("/api/regulations", json={
            "jenis": "Perbup", "nomor": "5", "tahun": 2025,
            "judul": "Tata Kelola", "status": "BERLAKU",
        })
        response = await auth_client.get("/api/regulations")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2
        assert isinstance(data["data"], list)

    @pytest.mark.asyncio
    async def test_get_regulation_detail(self, auth_client):
        create = await auth_client.post("/api/regulations", json={
            "jenis": "PP", "nomor": "12", "tahun": 2019,
            "judul": "Pengelolaan Keuangan Daerah", "status": "BERLAKU",
        })
        reg_id = create.json()["id"]
        response = await auth_client.get(f"/api/regulations/{reg_id}")
        assert response.status_code == 200
        assert response.json()["id"] == reg_id

    @pytest.mark.asyncio
    async def test_update_regulation(self, auth_client):
        create = await auth_client.post("/api/regulations", json={
            "jenis": "Perbup", "nomor": "2", "tahun": 2026,
            "judul": "Judul Awal", "status": "BERLAKU",
        })
        reg_id = create.json()["id"]
        response = await auth_client.put(f"/api/regulations/{reg_id}", json={
            "status": "DICABUT", "catatan": "Dicabut oleh Perbup baru"
        })
        assert response.status_code == 200
        assert response.json()["status"] == "DICABUT"

    @pytest.mark.asyncio
    async def test_delete_regulation(self, auth_client):
        create = await auth_client.post("/api/regulations", json={
            "jenis": "Perbup", "nomor": "999", "tahun": 2026,
            "judul": "Akan Dihapus", "status": "BERLAKU",
        })
        reg_id = create.json()["id"]
        response = await auth_client.delete(f"/api/regulations/{reg_id}")
        assert response.status_code == 204
        # Pastikan sudah terhapus
        get = await auth_client.get(f"/api/regulations/{reg_id}")
        assert get.status_code == 404

    @pytest.mark.asyncio
    async def test_create_invalid_jenis(self, auth_client):
        response = await auth_client.post("/api/regulations", json={
            "jenis": "INVALID", "judul": "Test", "status": "BERLAKU",
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_search_regulation(self, auth_client):
        await auth_client.post("/api/regulations", json={
            "jenis": "Permendagri", "nomor": "77", "tahun": 2020,
            "judul": "Pengelolaan Keuangan Daerah", "status": "BERLAKU",
        })
        response = await auth_client.get("/api/regulations/search/keyword?q=Keuangan")
        assert response.status_code == 200
        results = response.json()
        assert isinstance(results, list)
        assert any("Keuangan" in r["judul"] for r in results)

    @pytest.mark.asyncio
    async def test_filter_by_jenis(self, auth_client):
        await auth_client.post("/api/regulations", json={
            "jenis": "UU", "nomor": "1", "tahun": 2023,
            "judul": "UU Test Filter", "status": "BERLAKU",
        })
        response = await auth_client.get("/api/regulations?jenis=UU")
        assert response.status_code == 200
        data = response.json()
        assert all(r["jenis"] == "UU" for r in data["data"])

    @pytest.mark.asyncio
    async def test_unauthenticated_cannot_access(self, client):
        response = await client.get("/api/regulations")
        assert response.status_code == 401
