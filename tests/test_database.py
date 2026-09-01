"""
TALAS AI — Test Database
Test koneksi, model, dan integritas database.
"""
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class TestDatabaseConnection:
    """Test koneksi dan konfigurasi database."""

    @pytest.mark.asyncio
    async def test_database_is_accessible(self, test_engine):
        """Database harus dapat diakses."""
        async with test_engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            row = result.fetchone()
            assert row[0] == 1

    @pytest.mark.asyncio
    async def test_foreign_keys_enabled(self, test_engine):
        """Foreign keys harus aktif (SQLite default: off)."""
        async with test_engine.connect() as conn:
            result = await conn.execute(text("PRAGMA foreign_keys"))
            row = result.fetchone()
            assert row[0] == 1, "Foreign keys harus diaktifkan"

    @pytest.mark.asyncio
    async def test_wal_mode_enabled(self, test_engine):
        """WAL mode aktif untuk database file, tidak berlaku untuk in-memory."""
        async with test_engine.connect() as conn:
            result = await conn.execute(text("PRAGMA journal_mode"))
            row = result.fetchone()
            # In-memory SQLite menggunakan 'memory' journal mode — ini normal
            # WAL mode hanya berlaku untuk database berbasis file
            assert row[0].lower() in ("wal", "memory"), (
                f"Journal mode tidak dikenal: {row[0]}"
            )

    @pytest.mark.asyncio
    async def test_all_tables_created(self, test_engine):
        """Semua tabel yang didefinisikan di model harus ada."""
        expected_tables = [
            "users",
            "roles",
            "permissions",
            "user_roles",
            "role_permissions",
            "regulations",
            "regulation_relationships",
            "regulation_versions",
            "documents",
            "document_chunks",
            "document_metadata",
            "analyses",
            "analysis_findings",
            "analysis_sources",
            "chat_sessions",
            "chat_messages",
            "reviews",
            "review_comments",
            "reports",
            "report_versions",
            "audit_logs",
            "settings",
            "ai_providers",
            "ai_models",
            "ai_task_configs",
            "ai_usage_logs",
            "ai_fallback_logs",
        ]

        async with test_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            )
            actual_tables = {row[0] for row in result.fetchall()}

        for table in expected_tables:
            assert table in actual_tables, f"Tabel '{table}' tidak ditemukan di database"

    @pytest.mark.asyncio
    async def test_database_integrity(self, test_engine):
        """Database harus lulus integrity check."""
        async with test_engine.connect() as conn:
            result = await conn.execute(text("PRAGMA integrity_check(1)"))
            row = result.fetchone()
            assert row[0] == "ok", "Database integrity check gagal"


class TestDatabaseSession:
    """Test session management."""

    @pytest.mark.asyncio
    async def test_session_is_provided(self, db_session):
        """Session harus tersedia dari fixture."""
        assert db_session is not None
        assert isinstance(db_session, AsyncSession)

    @pytest.mark.asyncio
    async def test_session_can_execute_query(self, db_session):
        """Session harus dapat menjalankan query."""
        result = await db_session.execute(text("SELECT 1 + 1 AS result"))
        row = result.fetchone()
        assert row[0] == 2

    @pytest.mark.asyncio
    async def test_session_transaction_rollback(self, db_session):
        """Session harus dapat di-rollback."""
        from app.models.settings import AppSettings

        # Buat setting sementara
        setting = AppSettings(
            key="test_rollback_key",
            value="test_value",
            value_type="string",
            description="Test rollback",
            is_public=False,
        )
        db_session.add(setting)
        await db_session.flush()

        # Rollback
        await db_session.rollback()

        # Setting seharusnya tidak ada
        from sqlalchemy import select
        result = await db_session.execute(
            select(AppSettings).where(AppSettings.key == "test_rollback_key")
        )
        assert result.scalar_one_or_none() is None


class TestModels:
    """Test basic model operations."""

    @pytest.mark.asyncio
    async def test_create_role(self, db_session):
        """Harus dapat membuat role baru."""
        from app.models.user import Role
        from sqlalchemy import select

        role = Role(
            name="test_role",
            display_name="Test Role",
            description="Role untuk testing",
        )
        db_session.add(role)
        await db_session.flush()

        assert role.id is not None
        assert role.created_at is not None

    @pytest.mark.asyncio
    async def test_create_regulation(self, db_session):
        """Harus dapat membuat regulasi baru."""
        from app.models.regulation import Regulation
        from sqlalchemy import select

        reg = Regulation(
            jenis="Perbup",
            nomor="1",
            tahun=2026,
            judul="Peraturan Bupati Test",
            status="BERLAKU",
            level=8,
        )
        db_session.add(reg)
        await db_session.flush()

        assert reg.id is not None
        assert reg.uuid is not None  # UUID harus ter-generate otomatis

    @pytest.mark.asyncio
    async def test_regulation_uuid_unique(self, db_session):
        """Setiap regulasi harus memiliki UUID unik."""
        from app.models.regulation import Regulation

        reg1 = Regulation(
            jenis="Perbup", nomor="1", tahun=2024,
            judul="Test 1", status="BERLAKU", level=8,
        )
        reg2 = Regulation(
            jenis="Perbup", nomor="2", tahun=2024,
            judul="Test 2", status="BERLAKU", level=8,
        )
        db_session.add(reg1)
        db_session.add(reg2)
        await db_session.flush()

        assert reg1.uuid != reg2.uuid
