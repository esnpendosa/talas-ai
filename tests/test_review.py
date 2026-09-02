"""
TALAS AI — Tests for Human Review (Phase 13)
"""
from __future__ import annotations

import pytest
import uuid as _uuid


async def _make_user_with_perms(client, test_engine, *permissions):
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from app.models.user import User, Role, Permission, UserRole, RolePermission
    from app.services.security.hashing import hash_password

    suffix = _uuid.uuid4().hex[:6]
    factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)
    async with factory() as session:
        role = Role(name=f"role_{suffix}", display_name="Test Role")
        session.add(role)
        await session.flush()
        for perm_str in permissions:
            parts = perm_str.split(":")
            resource, action = parts[0], parts[1]
            perm = Permission(
                name=f"{resource}:{action}:{suffix}",
                resource=resource,
                action=action,
            )
            session.add(perm)
            await session.flush()
            session.add(RolePermission(role_id=role.id, permission_id=perm.id))
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


async def _make_finding(test_engine, status="AI_GENERATED"):
    """Buat analysis finding untuk testing."""
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from app.models.analysis import Analysis, AnalysisFinding
    from app.models.regulation import Regulation
    import uuid as _uuid

    factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)
    async with factory() as session:
        reg = Regulation(
            jenis="Raperbup", nomor=f"T-{_uuid.uuid4().hex[:4]}",
            tahun=2025, judul="Test Review", is_draft=True,
            status="BERLAKU", level=9,
        )
        session.add(reg)
        await session.flush()

        analysis = Analysis(
            regulation_id=reg.id,
            analysis_type="LEGAL_BASIS",
            status="COMPLETED",
        )
        session.add(analysis)
        await session.flush()

        finding = AnalysisFinding(
            analysis_id=analysis.id,
            pasal="Pasal 1",
            finding_type="LEGAL_BASIS",
            status="NEEDS_REVIEW",
            confidence=0.5,
            finding="TINJAUAN AWAL AI — WAJIB VERIFIKASI MANUSIA.\n\nAnalisis dasar hukum.",
            recommendation="Verifikasi manual diperlukan.",
            review_status=status,
        )
        session.add(finding)
        await session.commit()
        return finding.id


class TestHumanReview:
    @pytest.mark.asyncio
    async def test_review_requires_auth(self, client):
        """Review memerlukan autentikasi."""
        response = await client.post("/api/findings/1/review", json={
            "action": "TERIMA",
        })
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_review_invalid_action(self, client, test_engine):
        """Aksi tidak valid harus ditolak."""
        await _make_user_with_perms(client, test_engine, "review:create")
        finding_id = await _make_finding(test_engine)

        response = await client.post(f"/api/findings/{finding_id}/review", json={
            "action": "INVALID_ACTION",
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_review_finding_not_found(self, client, test_engine):
        """Review finding yang tidak ada harus 404."""
        await _make_user_with_perms(client, test_engine, "review:create")
        response = await client.post("/api/findings/9999/review", json={
            "action": "TERIMA",
        })
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_review_terima_sets_verified(self, client, test_engine):
        """Aksi TERIMA harus set review_status = VERIFIED."""
        await _make_user_with_perms(client, test_engine, "review:create")
        finding_id = await _make_finding(test_engine)

        response = await client.post(f"/api/findings/{finding_id}/review", json={
            "action": "TERIMA",
            "notes": "Dasar hukum sudah tepat.",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["new_review_status"] == "VERIFIED"

    @pytest.mark.asyncio
    async def test_review_verifikasi_sets_verified(self, client, test_engine):
        """Aksi VERIFIKASI harus set review_status = VERIFIED."""
        await _make_user_with_perms(client, test_engine, "review:create")
        finding_id = await _make_finding(test_engine)

        response = await client.post(f"/api/findings/{finding_id}/review", json={
            "action": "VERIFIKASI",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["new_review_status"] == "VERIFIED"

    @pytest.mark.asyncio
    async def test_review_tolak_sets_rejected(self, client, test_engine):
        """Aksi TOLAK harus set review_status = REJECTED."""
        await _make_user_with_perms(client, test_engine, "review:create")
        finding_id = await _make_finding(test_engine)

        response = await client.post(f"/api/findings/{finding_id}/review", json={
            "action": "TOLAK",
            "notes": "Analisis tidak akurat.",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["new_review_status"] == "REJECTED"

    @pytest.mark.asyncio
    async def test_review_edit_updates_finding(self, client, test_engine):
        """Aksi EDIT harus mengupdate finding dan set REVISED."""
        await _make_user_with_perms(client, test_engine, "review:create")
        finding_id = await _make_finding(test_engine)

        response = await client.post(f"/api/findings/{finding_id}/review", json={
            "action": "EDIT",
            "revised_finding": "Analisis direvisi oleh analis.",
            "notes": "Perlu klarifikasi.",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["new_review_status"] == "REVISED"

    @pytest.mark.asyncio
    async def test_review_komentar_sets_under_review(self, client, test_engine):
        """Aksi KOMENTAR harus set review_status = UNDER_REVIEW."""
        await _make_user_with_perms(client, test_engine, "review:create")
        finding_id = await _make_finding(test_engine)

        response = await client.post(f"/api/findings/{finding_id}/review", json={
            "action": "KOMENTAR",
            "notes": "Perlu konfirmasi tambahan.",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["new_review_status"] == "UNDER_REVIEW"

    @pytest.mark.asyncio
    async def test_verified_cannot_be_changed_by_regular_user(self, client, test_engine):
        """Finding VERIFIED tidak dapat diubah oleh non-superuser."""
        await _make_user_with_perms(client, test_engine, "review:create")
        finding_id = await _make_finding(test_engine, status="VERIFIED")

        response = await client.post(f"/api/findings/{finding_id}/review", json={
            "action": "TOLAK",
        })
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_review_response_has_disclaimer(self, client, test_engine):
        """Response review harus mengandung disclaimer."""
        await _make_user_with_perms(client, test_engine, "review:create")
        finding_id = await _make_finding(test_engine)

        response = await client.post(f"/api/findings/{finding_id}/review", json={
            "action": "KOMENTAR",
            "notes": "Test.",
        })
        assert response.status_code == 200
        data = response.json()
        assert "disclaimer" in data
        assert "WAJIB VERIFIKASI" in data["disclaimer"]
