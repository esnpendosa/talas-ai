"""
TALAS AI — Tests for Analysis (Phase 9-12)
Legal basis, conflict, consistency, comparison.
"""
from __future__ import annotations

import pytest
import uuid as _uuid


# ------------------------------------------------------------------ #
# Helper: user with permissions
# ------------------------------------------------------------------ #

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
        for resource, action in [p.split(":") for p in permissions]:
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


async def _make_regulation(test_engine, is_draft=True):
    """Buat regulation dan dokumen minimal untuk testing."""
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from app.models.regulation import Regulation
    from app.models.document import Document, DocumentChunk
    import uuid as _uuid

    factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)
    async with factory() as session:
        reg = Regulation(
            jenis="Raperbup",
            nomor=f"test-{_uuid.uuid4().hex[:4]}",
            tahun=2025,
            judul=f"Peraturan Test {_uuid.uuid4().hex[:4]}",
            is_draft=is_draft,
            status="BERLAKU",
            level=9,
        )
        session.add(reg)
        await session.flush()

        doc = Document(
            regulation_id=reg.id,
            original_filename="test.pdf",
            stored_filename=f"test_{_uuid.uuid4().hex}.pdf",
            file_path=f"/tmp/test_{_uuid.uuid4().hex}.pdf",
            file_size=1000,
            file_type="pdf",
            file_hash=_uuid.uuid4().hex,
            processing_status="COMPLETED",
        )
        session.add(doc)
        await session.flush()

        # Tambah beberapa chunks dengan pasal
        for i in range(1, 4):
            chunk = DocumentChunk(
                document_id=doc.id,
                text=f"Pasal {i} mengenai ketentuan umum. Setiap pejabat wajib melaksanakan.",
                text_length=50,
                chunk_index=i - 1,
                pasal=f"Pasal {i}",
            )
            session.add(chunk)

        await session.commit()
        return reg.id


# ------------------------------------------------------------------ #
# Phase 9 — Legal Basis Checker
# ------------------------------------------------------------------ #

class TestLegalBasisChecker:
    @pytest.mark.asyncio
    async def test_check_legal_basis_no_chunks(self, test_engine):
        """Legal basis checker dengan regulasi tanpa chunk."""
        from sqlalchemy.ext.asyncio import async_sessionmaker
        from app.models.analysis import Analysis
        from app.models.regulation import Regulation
        from app.services.analysis.legal_basis import check_legal_basis
        import uuid as _uuid

        factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)
        async with factory() as session:
            reg = Regulation(
                jenis="Raperbup",
                nomor=f"X-{_uuid.uuid4().hex[:4]}",
                tahun=2025,
                judul="Test Kosong",
                is_draft=True,
                status="BERLAKU",
                level=9,
            )
            session.add(reg)
            await session.flush()

            analysis = Analysis(
                regulation_id=reg.id,
                analysis_type="LEGAL_BASIS",
                status="PROCESSING",
            )
            session.add(analysis)
            await session.commit()
            analysis_id = analysis.id
            reg_id = reg.id

        async with factory() as session:
            count = await check_legal_basis(session, reg_id, analysis_id)
            assert count >= 1

    @pytest.mark.asyncio
    async def test_check_legal_basis_with_chunks(self, test_engine):
        """Legal basis checker dengan chunk yang memiliki pasal."""
        from sqlalchemy.ext.asyncio import async_sessionmaker
        from app.models.analysis import Analysis, AnalysisFinding
        from app.services.analysis.legal_basis import check_legal_basis, DISCLAIMER
        from app.services.rag.search import ensure_fts_table
        from sqlalchemy import select

        factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)
        reg_id = await _make_regulation(test_engine)

        async with factory() as session:
            await ensure_fts_table(session)
            analysis = Analysis(
                regulation_id=reg_id,
                analysis_type="LEGAL_BASIS",
                status="PROCESSING",
            )
            session.add(analysis)
            await session.commit()
            analysis_id = analysis.id

        async with factory() as session:
            count = await check_legal_basis(session, reg_id, analysis_id)
            assert count >= 1

            # Periksa findings yang dibuat
            result = await session.execute(
                select(AnalysisFinding)
                .where(AnalysisFinding.analysis_id == analysis_id)
            )
            findings = result.scalars().all()
            assert len(findings) >= 1

            for f in findings:
                assert f.finding_type == "LEGAL_BASIS"
                assert f.status in ("FOUND", "NOT_FOUND", "NEEDS_REVIEW")
                assert f.finding is not None
                assert DISCLAIMER in f.finding

    @pytest.mark.asyncio
    async def test_legal_basis_no_illegal_status(self, test_engine):
        """Status tidak boleh LEGAL atau ILLEGAL."""
        from sqlalchemy.ext.asyncio import async_sessionmaker
        from app.models.analysis import Analysis, AnalysisFinding
        from app.services.analysis.legal_basis import check_legal_basis
        from sqlalchemy import select

        factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)
        reg_id = await _make_regulation(test_engine)

        async with factory() as session:
            analysis = Analysis(
                regulation_id=reg_id,
                analysis_type="LEGAL_BASIS",
                status="PROCESSING",
            )
            session.add(analysis)
            await session.commit()
            analysis_id = analysis.id

        async with factory() as session:
            await check_legal_basis(session, reg_id, analysis_id)
            result = await session.execute(
                select(AnalysisFinding)
                .where(AnalysisFinding.analysis_id == analysis_id)
            )
            findings = result.scalars().all()
            for f in findings:
                assert f.status not in ("LEGAL", "ILLEGAL", "SAH", "TIDAK_SAH")


# ------------------------------------------------------------------ #
# Phase 10 — Conflict Checker
# ------------------------------------------------------------------ #

class TestConflictChecker:
    @pytest.mark.asyncio
    async def test_check_conflicts_returns_findings(self, test_engine):
        """Conflict checker harus menghasilkan findings."""
        from sqlalchemy.ext.asyncio import async_sessionmaker
        from app.models.analysis import Analysis, AnalysisFinding
        from app.services.analysis.conflict import check_conflicts
        from sqlalchemy import select

        factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)
        reg_id = await _make_regulation(test_engine)

        async with factory() as session:
            analysis = Analysis(
                regulation_id=reg_id,
                analysis_type="CONFLICT",
                status="PROCESSING",
            )
            session.add(analysis)
            await session.commit()
            analysis_id = analysis.id

        async with factory() as session:
            count = await check_conflicts(session, reg_id, analysis_id)
            assert count >= 1

            result = await session.execute(
                select(AnalysisFinding)
                .where(AnalysisFinding.analysis_id == analysis_id)
            )
            findings = result.scalars().all()
            for f in findings:
                assert f.finding_type == "CONFLICT"
                assert f.status in (
                    "NO_ISSUE", "DIFFERENCE", "POTENTIAL_CONFLICT", "NEEDS_REVIEW"
                )

    @pytest.mark.asyncio
    async def test_conflict_no_absolute_bertentangan(self, test_engine):
        """Finding tidak boleh menyatakan 'bertentangan' secara absolut."""
        from sqlalchemy.ext.asyncio import async_sessionmaker
        from app.models.analysis import Analysis, AnalysisFinding
        from app.services.analysis.conflict import check_conflicts
        from sqlalchemy import select

        factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)
        reg_id = await _make_regulation(test_engine)

        async with factory() as session:
            analysis = Analysis(
                regulation_id=reg_id,
                analysis_type="CONFLICT",
                status="PROCESSING",
            )
            session.add(analysis)
            await session.commit()
            analysis_id = analysis.id

        async with factory() as session:
            await check_conflicts(session, reg_id, analysis_id)
            result = await session.execute(
                select(AnalysisFinding)
                .where(AnalysisFinding.analysis_id == analysis_id)
            )
            findings = result.scalars().all()
            for f in findings:
                # Status tidak boleh menggunakan ILLEGAL atau LEGAL
                assert f.status not in ("LEGAL", "ILLEGAL")


# ------------------------------------------------------------------ #
# Phase 11 — Consistency Checker
# ------------------------------------------------------------------ #

class TestConsistencyChecker:
    @pytest.mark.asyncio
    async def test_check_consistency_returns_findings(self, test_engine):
        """Consistency checker harus menghasilkan findings."""
        from sqlalchemy.ext.asyncio import async_sessionmaker
        from app.models.analysis import Analysis, AnalysisFinding
        from app.services.analysis.consistency import check_consistency
        from sqlalchemy import select

        factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)
        reg_id = await _make_regulation(test_engine)

        async with factory() as session:
            analysis = Analysis(
                regulation_id=reg_id,
                analysis_type="CONSISTENCY",
                status="PROCESSING",
            )
            session.add(analysis)
            await session.commit()
            analysis_id = analysis.id

        async with factory() as session:
            count = await check_consistency(session, reg_id, analysis_id)
            assert count >= 1

            result = await session.execute(
                select(AnalysisFinding)
                .where(AnalysisFinding.analysis_id == analysis_id)
            )
            findings = result.scalars().all()
            for f in findings:
                assert f.finding_type == "CONSISTENCY"
                assert f.status in ("NO_ISSUE", "DIFFERENCE", "NEEDS_REVIEW")


# ------------------------------------------------------------------ #
# Phase 12 — Comparison Engine
# ------------------------------------------------------------------ #

class TestComparisonEngine:
    @pytest.mark.asyncio
    async def test_compare_regulations(self, test_engine):
        """Comparison engine harus menghasilkan perbandingan."""
        from app.services.analysis.comparison import compare_regulations, DISCLAIMER
        from sqlalchemy.ext.asyncio import async_sessionmaker

        factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)

        reg_id_a = await _make_regulation(test_engine)
        reg_id_b = await _make_regulation(test_engine)

        async with factory() as session:
            result = await compare_regulations(session, reg_id_a, reg_id_b)

        assert "disclaimer" in result
        assert DISCLAIMER in result["disclaimer"]
        assert "stats" in result
        assert "results" in result
        assert result["regulation_id_a"] == reg_id_a
        assert result["regulation_id_b"] == reg_id_b

    @pytest.mark.asyncio
    async def test_compare_categories_valid(self, test_engine):
        """Kategori perbandingan harus valid."""
        from app.services.analysis.comparison import compare_regulations
        from sqlalchemy.ext.asyncio import async_sessionmaker

        factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)
        reg_id_a = await _make_regulation(test_engine)
        reg_id_b = await _make_regulation(test_engine)

        valid_categories = {"UNCHANGED", "CHANGED", "ADDED", "REMOVED", "NEEDS_REVIEW"}

        async with factory() as session:
            result = await compare_regulations(session, reg_id_a, reg_id_b)

        for item in result.get("results", []):
            assert item["category"] in valid_categories

    @pytest.mark.asyncio
    async def test_compare_empty_regulations(self, test_engine):
        """Perbandingan dengan regulasi kosong harus graceful."""
        from app.services.analysis.comparison import compare_regulations, DISCLAIMER
        from sqlalchemy.ext.asyncio import async_sessionmaker
        from app.models.regulation import Regulation
        import uuid as _uuid

        factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)

        # Buat dua regulasi kosong (tanpa dokumen)
        async with factory() as session:
            reg_a = Regulation(
                jenis="UU", nomor=f"{_uuid.uuid4().hex[:4]}",
                tahun=2020, judul="UU Test A", is_draft=False,
                status="BERLAKU", level=1,
            )
            reg_b = Regulation(
                jenis="UU", nomor=f"{_uuid.uuid4().hex[:4]}",
                tahun=2021, judul="UU Test B", is_draft=False,
                status="BERLAKU", level=1,
            )
            session.add_all([reg_a, reg_b])
            await session.commit()
            rid_a, rid_b = reg_a.id, reg_b.id

        async with factory() as session:
            result = await compare_regulations(session, rid_a, rid_b)

        assert DISCLAIMER in result["disclaimer"]
        assert result["total_pasals"] == 0


# ------------------------------------------------------------------ #
# Phase 9-12 — API Endpoints
# ------------------------------------------------------------------ #

class TestAnalysisAPI:
    @pytest.mark.asyncio
    async def test_start_analysis_requires_auth(self, client):
        """Start analysis memerlukan autentikasi."""
        response = await client.post("/api/analysis", json={
            "regulation_id": 1,
            "analysis_type": "LEGAL_BASIS",
        })
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_start_analysis_invalid_type(self, client, test_engine):
        """Tipe analisis tidak valid harus ditolak."""
        await _make_user_with_perms(client, test_engine, "analysis:create")
        response = await client.post("/api/analysis", json={
            "regulation_id": 1,
            "analysis_type": "INVALID_TYPE",
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_start_analysis_success(self, client, test_engine):
        """Start analysis dengan data valid harus berhasil."""
        await _make_user_with_perms(client, test_engine, "analysis:create")
        reg_id = await _make_regulation(test_engine)

        response = await client.post("/api/analysis", json={
            "regulation_id": reg_id,
            "analysis_type": "LEGAL_BASIS",
        })
        assert response.status_code == 202
        data = response.json()
        assert "analysis_id" in data
        assert "disclaimer" in data
        assert "WAJIB VERIFIKASI" in data["disclaimer"]

    @pytest.mark.asyncio
    async def test_get_analysis_not_found(self, client, test_engine):
        """Get analysis yang tidak ada harus 404."""
        await _make_user_with_perms(client, test_engine, "analysis:read")
        response = await client.get("/api/analysis/9999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_analysis_success(self, client, test_engine):
        """Get analysis yang ada harus berhasil."""
        await _make_user_with_perms(client, test_engine, "analysis:create", "analysis:read")
        reg_id = await _make_regulation(test_engine)

        create_resp = await client.post("/api/analysis", json={
            "regulation_id": reg_id,
            "analysis_type": "LEGAL_BASIS",
        })
        analysis_id = create_resp.json()["analysis_id"]

        response = await client.get(f"/api/analysis/{analysis_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == analysis_id

    @pytest.mark.asyncio
    async def test_list_findings(self, client, test_engine):
        """List findings untuk analisis yang ada."""
        await _make_user_with_perms(client, test_engine, "analysis:create", "analysis:read")
        reg_id = await _make_regulation(test_engine)

        create_resp = await client.post("/api/analysis", json={
            "regulation_id": reg_id,
            "analysis_type": "LEGAL_BASIS",
        })
        analysis_id = create_resp.json()["analysis_id"]

        response = await client.get(f"/api/analysis/{analysis_id}/findings")
        assert response.status_code == 200
        data = response.json()
        assert "findings" in data
        assert "disclaimer" in data

    @pytest.mark.asyncio
    async def test_compare_endpoint(self, client, test_engine):
        """Endpoint compare regulations harus berfungsi."""
        await _make_user_with_perms(client, test_engine, "analysis:read")
        reg_id_a = await _make_regulation(test_engine)
        reg_id_b = await _make_regulation(test_engine)

        response = await client.post("/api/analysis/compare", json={
            "regulation_id_a": reg_id_a,
            "regulation_id_b": reg_id_b,
        })
        assert response.status_code == 200
        data = response.json()
        assert "stats" in data
        assert "disclaimer" in data
