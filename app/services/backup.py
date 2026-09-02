"""
TALAS AI — Backup Service (Phase 16)
Backup dan restore database SQLite.

PRINSIP:
- Backup otomatis ke data/backups/
- Maksimal 10 backup, yang lama dihapus
- Restore memerlukan konfirmasi eksplisit
- Tidak ada operasi destruktif tanpa konfirmasi
"""
from __future__ import annotations

import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from app.config import settings

logger = logging.getLogger("talas_ai.backup")

MAX_BACKUPS = settings.MAX_BACKUPS


def get_db_path() -> Path:
    """Dapatkan path database utama."""
    db_url = settings.DATABASE_URL
    # sqlite:///./data/talas.db → ./data/talas.db
    db_path = db_url.replace("sqlite:///", "")
    return Path(db_path).resolve()


def get_backup_dir() -> Path:
    """Dapatkan direktori backup."""
    backup_dir = Path(settings.BACKUP_DIR)
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def list_backups() -> List[dict]:
    """Daftar semua file backup yang ada."""
    backup_dir = get_backup_dir()
    backups = []

    for f in sorted(backup_dir.glob("backup_*.db"), reverse=True):
        stat = f.stat()
        backups.append({
            "filename": f.name,
            "path": str(f),
            "size_bytes": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        })

    return backups


def create_backup() -> dict:
    """
    Buat backup database SQLite.
    Copy file DB ke data/backups/backup_YYYY-MM-DD_HH-MM-SS.db.
    Hapus backup lama jika melebihi MAX_BACKUPS.

    Returns: info backup yang dibuat
    """
    db_path = get_db_path()
    if not db_path.exists():
        raise FileNotFoundError(f"Database tidak ditemukan: {db_path}")

    backup_dir = get_backup_dir()
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    backup_filename = f"backup_{ts}.db"
    backup_path = backup_dir / backup_filename

    # Copy database file
    shutil.copy2(str(db_path), str(backup_path))
    file_size = backup_path.stat().st_size

    logger.info(f"Backup created: {backup_path} ({file_size} bytes)")

    # Hapus backup lama jika melebihi batas
    _cleanup_old_backups(backup_dir)

    return {
        "success": True,
        "filename": backup_filename,
        "path": str(backup_path),
        "size_bytes": file_size,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def restore_backup(backup_path: str, confirmed: bool = False) -> dict:
    """
    Restore database dari backup.

    PERINGATAN: Operasi ini menggantikan database saat ini.
    Memerlukan konfirmasi eksplisit (confirmed=True).

    Args:
        backup_path: Path ke file backup
        confirmed: Harus True untuk melanjutkan

    Returns: info restore
    """
    if not confirmed:
        raise PermissionError(
            "Restore memerlukan konfirmasi eksplisit. "
            "Set confirmed=True untuk melanjutkan. "
            "PERINGATAN: Database saat ini akan digantikan."
        )

    backup_file = Path(backup_path)
    if not backup_file.exists():
        raise FileNotFoundError(f"File backup tidak ditemukan: {backup_path}")

    if not backup_file.name.startswith("backup_") or not backup_file.suffix == ".db":
        raise ValueError("File backup tidak valid. Harus berformat backup_YYYY-MM-DD_HH-MM-SS.db")

    db_path = get_db_path()

    # Buat backup dari database saat ini sebelum restore
    pre_restore_backup = None
    if db_path.exists():
        try:
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
            pre_restore_path = backup_file.parent / f"pre_restore_{ts}.db"
            shutil.copy2(str(db_path), str(pre_restore_path))
            pre_restore_backup = str(pre_restore_path)
            logger.info(f"Pre-restore backup created: {pre_restore_path}")
        except Exception as e:
            logger.warning(f"Could not create pre-restore backup: {e}")

    # Lakukan restore
    shutil.copy2(str(backup_file), str(db_path))
    logger.info(f"Database restored from: {backup_file}")

    return {
        "success": True,
        "restored_from": str(backup_file),
        "database_path": str(db_path),
        "pre_restore_backup": pre_restore_backup,
        "message": "Database berhasil direstore. Restart aplikasi untuk menggunakan database yang direstored.",
    }


def _cleanup_old_backups(backup_dir: Path) -> None:
    """Hapus backup lama jika melebihi MAX_BACKUPS."""
    backups = sorted(backup_dir.glob("backup_*.db"), reverse=True)
    if len(backups) > MAX_BACKUPS:
        for old_backup in backups[MAX_BACKUPS:]:
            try:
                old_backup.unlink()
                logger.info(f"Old backup removed: {old_backup}")
            except Exception as e:
                logger.warning(f"Could not remove old backup {old_backup}: {e}")
