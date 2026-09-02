"""
TALAS AI — Tests for Dashboard (Phase 15)
"""
from __future__ import annotations

import pytest
import uuid as _uuid


async def _make_user(client, test_engine):
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from app.models.user import User, Role, UserRole
    from app.services.security.hashing import hash_password

    suffix = _uuid.uuid4().hex[:6]
    factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)
    async with factory() as session:
        role = Role(name=f"role_{suffix}", display_name="Test")
        session.add(role)
        await session.flush()
        user = User(
            username=f"u_{suffix}",
            email=f"u_{suffix}@t.local",
            full_name="Test",
            hashed_password=hash_password("Pass@123"),
            is_active=True,
        )
        session.add(user)
        await session.flush()
        session.add(UserRole(user_id=user.id, role_id=role.id))
        await session.commit()

    login = await client.post(
        "/api/auth/login",
        json={"username": f"u_{suffix}", "password": "Pass@123"},
    )
    token = login.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


class TestDashboard:
    @pytest.mark.asyncio
    async def test_dashboard_requires_auth(self, client):
        """Dashboard stats memerlukan autentikasi."""
        response = await client.get("/api/dashboard/stats")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_dashboard_stats_structure(self, client, test_engine):
        """Dashboard stats harus memiliki struktur yang benar."""
        await _make_user(client, test_engine)
        response = await client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()

        required_fields = [
            "total_regulasi",
            "total_raperbup",
            "telaah_selesai",
            "perlu_review",
            "potensi_konflik",
            "ketidakkonsistenan",
        ]
        for field in required_fields:
            assert field in data, f"Field '{field}' tidak ada dalam response"

    @pytest.mark.asyncio
    async def test_dashboard_stats_numeric_values(self, client, test_engine):
        """Semua nilai statistik harus numerik."""
        await _make_user(client, test_engine)
        response = await client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()

        numeric_fields = [
            "total_regulasi", "total_raperbup", "telaah_selesai",
            "perlu_review", "potensi_konflik", "ketidakkonsistenan",
        ]
        for field in numeric_fields:
            assert isinstance(data[field], int), f"Field '{field}' bukan integer"
            assert data[field] >= 0, f"Field '{field}' tidak boleh negatif"

    @pytest.mark.asyncio
    async def test_dashboard_counts_raperbup(self, client, test_engine):
        """Dashboard harus menghitung raperbup dengan benar."""
        from sqlalchemy.ext.asyncio import async_sessionmaker
        from app.models.regulation import Regulation

        factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)

        # Buat beberapa regulasi
        async with factory() as session:
            for i in range(3):
                reg = Regulation(
                    jenis="Raperbup",
                    nomor=f"D-{_uuid.uuid4().hex[:4]}",
                    tahun=2025,
                    judul=f"Raperbup Test {i}",
                    is_draft=True,
                    status="BERLAKU",
                    level=9,
                )
                session.add(reg)
            await session.commit()

        await _make_user(client, test_engine)
        response = await client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_raperbup"] >= 3

    @pytest.mark.asyncio
    async def test_dashboard_has_disclaimer(self, client, test_engine):
        """Dashboard response harus memuat disclaimer."""
        await _make_user(client, test_engine)
        response = await client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert "disclaimer" in data
        assert "WAJIB VERIFIKASI" in data["disclaimer"]

    @pytest.mark.asyncio
    async def test_dashboard_counts_completed_analyses(self, client, test_engine):
        """Dashboard harus menghitung analisis selesai dengan benar."""
        from sqlalchemy.ext.asyncio import async_sessionmaker
        from app.models.analysis import Analysis
        from app.models.regulation import Regulation

        factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)

        async with factory() as session:
            reg = Regulation(
                jenis="Raperbup", nomor=f"A-{_uuid.uuid4().hex[:4]}",
                tahun=2025, judul="Test Analysis", is_draft=True,
                status="BERLAKU", level=9,
            )
            session.add(reg)
            await session.flush()
            analysis = Analysis(
                regulation_id=reg.id,
                analysis_type="FULL",
                status="COMPLETED",
            )
            session.add(analysis)
            await session.commit()

        await _make_user(client, test_engine)
        response = await client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["telaah_selesai"] >= 1
