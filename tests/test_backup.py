"""
TALAS AI — Tests for Backup and Restore (Phase 16)
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
import uuid as _uuid


async def _make_superuser(client, test_engine):
    """Buat superuser untuk testing admin endpoints."""
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from app.models.user import User, Role, UserRole
    from app.services.security.hashing import hash_password

    suffix = _uuid.uuid4().hex[:6]
    factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)
    async with factory() as session:
        role = Role(name=f"admin_{suffix}", display_name="Admin")
        session.add(role)
        await session.flush()
        user = User(
            username=f"admin_{suffix}",
            email=f"admin_{suffix}@t.local",
            full_name="Admin",
            hashed_password=hash_password("Pass@123"),
            is_active=True,
            is_superuser=True,
        )
        session.add(user)
        await session.flush()
        session.add(UserRole(user_id=user.id, role_id=role.id))
        await session.commit()

    login = await client.post(
        "/api/auth/login",
        json={"username": f"admin_{suffix}", "password": "Pass@123"},
    )
    token = login.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


class TestBackupService:
    def test_create_backup_success(self, tmp_path):
        """Backup harus berhasil jika database ada."""
        import app.services.backup as bkp_module

        # Buat file DB tiruan
        db_file = tmp_path / "talas.db"
        db_file.write_text("fake sqlite db content")

        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        # Patch fungsi
        original_get_db = bkp_module.get_db_path
        original_get_bkp = bkp_module.get_backup_dir
        bkp_module.get_db_path = lambda: db_file
        bkp_module.get_backup_dir = lambda: backup_dir

        try:
            result = bkp_module.create_backup()
            assert result["success"] is True
            assert "filename" in result
            assert result["filename"].startswith("backup_")
            assert result["filename"].endswith(".db")
            assert Path(result["path"]).exists()
        finally:
            bkp_module.get_db_path = original_get_db
            bkp_module.get_backup_dir = original_get_bkp

    def test_create_backup_db_not_found(self, tmp_path):
        """Backup harus gagal jika database tidak ada."""
        import app.services.backup as bkp_module

        original_get_db = bkp_module.get_db_path
        bkp_module.get_db_path = lambda: tmp_path / "nonexistent.db"

        try:
            with pytest.raises(FileNotFoundError):
                bkp_module.create_backup()
        finally:
            bkp_module.get_db_path = original_get_db

    def test_restore_requires_confirmation(self, tmp_path):
        """Restore tanpa konfirmasi harus ditolak."""
        from app.services.backup import restore_backup

        backup_file = tmp_path / "backup_2025-01-01_00-00-00.db"
        backup_file.write_text("backup content")

        with pytest.raises(PermissionError):
            restore_backup(str(backup_file), confirmed=False)

    def test_restore_invalid_filename(self, tmp_path):
        """Restore dengan filename tidak valid harus ditolak."""
        from app.services.backup import restore_backup

        bad_file = tmp_path / "not_a_backup.db"
        bad_file.write_text("data")

        with pytest.raises(ValueError):
            restore_backup(str(bad_file), confirmed=True)

    def test_restore_file_not_found(self):
        """Restore file yang tidak ada harus FileNotFoundError."""
        from app.services.backup import restore_backup

        with pytest.raises(FileNotFoundError):
            restore_backup("/nonexistent/backup_2025-01-01_00-00-00.db", confirmed=True)

    def test_list_backups(self, tmp_path):
        """list_backups harus mengembalikan list backup."""
        import app.services.backup as bkp_module

        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        # Buat beberapa file backup
        (backup_dir / "backup_2025-01-01_00-00-00.db").write_text("b1")
        (backup_dir / "backup_2025-01-02_00-00-00.db").write_text("b2")

        original_get_bkp = bkp_module.get_backup_dir
        bkp_module.get_backup_dir = lambda: backup_dir

        try:
            backups = bkp_module.list_backups()
            assert len(backups) == 2
            for b in backups:
                assert "filename" in b
                assert "path" in b
                assert "size_bytes" in b
        finally:
            bkp_module.get_backup_dir = original_get_bkp

    def test_cleanup_old_backups(self, tmp_path):
        """Backup lama harus dihapus jika melebihi batas."""
        import app.services.backup as bkp_module

        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        # Buat 15 file backup (MAX = 10)
        for i in range(15):
            (backup_dir / f"backup_2025-01-{i+1:02d}_00-00-00.db").write_text(f"b{i}")

        bkp_module._cleanup_old_backups(backup_dir)

        remaining = list(backup_dir.glob("backup_*.db"))
        assert len(remaining) <= bkp_module.MAX_BACKUPS


class TestBackupAPI:
    @pytest.mark.asyncio
    async def test_backup_requires_auth(self, client):
        """Backup memerlukan autentikasi."""
        response = await client.post("/api/backup")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_backup_requires_admin(self, client, test_engine):
        """Backup hanya untuk admin."""
        from sqlalchemy.ext.asyncio import async_sessionmaker
        from app.models.user import User, Role, UserRole
        from app.services.security.hashing import hash_password

        suffix = _uuid.uuid4().hex[:6]
        factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)
        async with factory() as session:
            role = Role(name=f"regular_{suffix}", display_name="Regular")
            session.add(role)
            await session.flush()
            user = User(
                username=f"reg_{suffix}",
                email=f"reg_{suffix}@t.local",
                full_name="Regular",
                hashed_password=hash_password("Pass@123"),
                is_active=True,
                is_superuser=False,
            )
            session.add(user)
            await session.flush()
            session.add(UserRole(user_id=user.id, role_id=role.id))
            await session.commit()

        login = await client.post(
            "/api/auth/login",
            json={"username": f"reg_{suffix}", "password": "Pass@123"},
        )
        token = login.json()["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})

        response = await client.post("/api/backup")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_restore_without_confirmation(self, client, test_engine):
        """Restore tanpa konfirmasi text harus ditolak."""
        await _make_superuser(client, test_engine)
        response = await client.post("/api/restore", json={
            "backup_path": "/tmp/backup_2025-01-01_00-00-00.db",
            "confirmed": True,
            "confirmation_text": "WRONG CONFIRMATION",
        })
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_list_backups_admin(self, client, test_engine):
        """List backups hanya untuk admin."""
        await _make_superuser(client, test_engine)
        response = await client.get("/api/backup/list")
        assert response.status_code == 200
        data = response.json()
        assert "backups" in data
