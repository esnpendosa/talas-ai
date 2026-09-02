"""
TALAS AI — Tests for Report Generation (Phase 14)
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


async def _create_completed_analysis(test_engine):
    """Buat analisis yang sudah selesai untuk testing report."""
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from app.models.analysis import Analysis, AnalysisFinding
    from app.models.regulation import Regulation

    factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)
    async with factory() as session:
        reg = Regulation(
            jenis="Raperbup", nomor=f"R-{_uuid.uuid4().hex[:4]}",
            tahun=2025, judul="Test Report Regulation",
            is_draft=True, status="BERLAKU", level=9,
        )
        session.add(reg)
        await session.flush()

        analysis = Analysis(
            regulation_id=reg.id,
            analysis_type="FULL",
            status="COMPLETED",
            total_articles=3,
            found_legal_basis=2,
            needs_review_count=1,
            potential_conflicts=0,
            inconsistencies=1,
        )
        session.add(analysis)
        await session.flush()

        # Tambah beberapa findings
        for i, (ftype, fstatus) in enumerate([
            ("LEGAL_BASIS", "FOUND"),
            ("LEGAL_BASIS", "NOT_FOUND"),
            ("CONFLICT", "NO_ISSUE"),
            ("CONSISTENCY", "DIFFERENCE"),
        ]):
            finding = AnalysisFinding(
                analysis_id=analysis.id,
                pasal=f"Pasal {i+1}",
                finding_type=ftype,
                status=fstatus,
                confidence=0.8,
                finding=f"TINJAUAN AWAL AI — WAJIB VERIFIKASI MANUSIA.\n\nFinding {i+1}.",
                recommendation=f"Rekomendasi {i+1}.",
                review_status="AI_GENERATED",
            )
            session.add(finding)

        await session.commit()
        return analysis.id


class TestReportGeneration:
    @pytest.mark.asyncio
    async def test_generate_report_requires_auth(self, client):
        """Generate report memerlukan autentikasi."""
        response = await client.post("/api/reports/generate", json={
            "analysis_id": 1,
            "format": "json",
        })
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_generate_report_json_format(self, client, test_engine):
        """Generate report dalam format JSON harus berhasil."""
        await _make_user_with_perms(client, test_engine, "reports:create", "reports:read")
        analysis_id = await _create_completed_analysis(test_engine)

        response = await client.post("/api/reports/generate", json={
            "analysis_id": analysis_id,
            "format": "json",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "report_id" in data
        assert data["format"] == "json"
        assert "disclaimer" in data

    @pytest.mark.asyncio
    async def test_generate_report_not_found(self, client, test_engine):
        """Generate report untuk analisis yang tidak ada harus 404."""
        await _make_user_with_perms(client, test_engine, "reports:create")
        response = await client.post("/api/reports/generate", json={
            "analysis_id": 99999,
            "format": "json",
        })
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_report_data_has_disclaimer(self, test_engine):
        """Data laporan harus memuat disclaimer di setiap section."""
        from sqlalchemy.ext.asyncio import async_sessionmaker
        from app.services.reports.generator import _build_report_data, DISCLAIMER
        from app.models.analysis import Analysis

        factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)
        analysis_id = await _create_completed_analysis(test_engine)

        async with factory() as session:
            from sqlalchemy import select
            from app.models.analysis import AnalysisFinding
            result = await session.execute(
                select(Analysis).where(Analysis.id == analysis_id)
            )
            analysis = result.scalar_one()
            findings_result = await session.execute(
                select(AnalysisFinding).where(AnalysisFinding.analysis_id == analysis_id)
            )
            findings = findings_result.scalars().all()

        report_data = _build_report_data(analysis, None, findings)
        assert report_data["disclaimer"] == DISCLAIMER
        sections = report_data["sections"]
        assert "VIII_KESIMPULAN" in sections
        assert DISCLAIMER in sections["VIII_KESIMPULAN"]["disclaimer"]

    @pytest.mark.asyncio
    async def test_generate_report_docx_fallback(self, client, test_engine):
        """Generate report DOCX fallback ke JSON jika python-docx tidak tersedia."""
        await _make_user_with_perms(client, test_engine, "reports:create")
        analysis_id = await _create_completed_analysis(test_engine)

        response = await client.post("/api/reports/generate", json={
            "analysis_id": analysis_id,
            "format": "docx",  # Akan fallback ke JSON jika python-docx tidak ada
        })
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["format"] in ("docx", "json")  # Bisa fallback

    @pytest.mark.asyncio
    async def test_list_reports(self, client, test_engine):
        """List reports harus berfungsi."""
        await _make_user_with_perms(client, test_engine, "reports:create", "reports:read")
        analysis_id = await _create_completed_analysis(test_engine)

        # Generate report dulu
        await client.post("/api/reports/generate", json={
            "analysis_id": analysis_id,
            "format": "json",
        })

        response = await client.get("/api/reports")
        assert response.status_code == 200
        data = response.json()
        assert "reports" in data
        assert "total" in data
