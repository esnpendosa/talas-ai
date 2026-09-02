"""
TALAS AI — Backup & Restore API (Phase 16)
Endpoints untuk backup dan restore database. Hanya admin.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.dependencies import require_superuser
from app.models.user import User

logger = logging.getLogger("talas_ai.api.backup")

router = APIRouter(tags=["admin", "backup"])


class RestoreRequest(BaseModel):
    backup_path: str
    confirmed: bool = False
    confirmation_text: str = ""
    # confirmation_text harus "SAYA KONFIRMASI RESTORE DATABASE"


REQUIRED_CONFIRMATION = "SAYA KONFIRMASI RESTORE DATABASE"


@router.post(
    "/backup",
    status_code=status.HTTP_201_CREATED,
    summary="Buat backup database (admin only)",
)
async def create_backup_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_superuser()),
):
    """Buat backup database SQLite. Hanya administrator."""
    from app.services.backup import create_backup

    try:
        result = create_backup()

        # Log audit
        try:
            from app.services.security.audit_service import log_action
            await log_action(
                db=db,
                user_id=current_user.id,
                action="CREATE_BACKUP",
                resource_type="database",
                resource_id="talas.db",
                details=f"backup_file={result.get('filename')}",
                ip=None,
                status="SUCCESS",
            )
            await db.commit()
        except Exception:
            pass

        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Backup gagal: {str(e)}")


@router.get(
    "/backup/list",
    summary="Daftar file backup (admin only)",
)
async def list_backups_endpoint(
    current_user: User = Depends(require_superuser()),
):
    """Daftar semua file backup yang tersedia."""
    from app.services.backup import list_backups
    return {
        "backups": list_backups(),
        "message": "Gunakan path dari daftar di atas untuk restore.",
    }


@router.post(
    "/restore",
    summary="Restore database dari backup (admin only)",
)
async def restore_backup_endpoint(
    request: RestoreRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_superuser()),
):
    """
    Restore database dari file backup.

    PERINGATAN: Operasi ini menggantikan database saat ini secara permanen.
    Memerlukan konfirmasi eksplisit.
    """
    if not request.confirmed:
        raise HTTPException(
            status_code=400,
            detail="Konfirmasi diperlukan. Set confirmed=true dalam request body.",
        )

    if request.confirmation_text != REQUIRED_CONFIRMATION:
        raise HTTPException(
            status_code=400,
            detail=f"confirmation_text harus: '{REQUIRED_CONFIRMATION}'",
        )

    from app.services.backup import restore_backup

    try:
        result = restore_backup(request.backup_path, confirmed=True)

        # Log audit
        try:
            from app.services.security.audit_service import log_action
            await log_action(
                db=db,
                user_id=current_user.id,
                action="RESTORE_BACKUP",
                resource_type="database",
                resource_id="talas.db",
                details=f"restored_from={request.backup_path}",
                ip=None,
                status="SUCCESS",
            )
            await db.commit()
        except Exception:
            pass

        return result

    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Restore failed: {e}")
        raise HTTPException(status_code=500, detail=f"Restore gagal: {str(e)}")
