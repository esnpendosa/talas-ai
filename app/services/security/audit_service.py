"""
TALAS AI — Audit Service (Phase 16)
Catat semua aksi penting pengguna dan sistem.

PENTING:
- Jangan simpan password, API key, atau isi dokumen lengkap
- Jangan simpan PII yang tidak diperlukan
- Audit log adalah append-only (tidak ada delete)
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog

logger = logging.getLogger("talas_ai.audit")


async def log_action(
    db: AsyncSession,
    user_id: Optional[int],
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[str] = None,
    ip: Optional[str] = None,
    status: str = "SUCCESS",
    username: Optional[str] = None,
    user_agent: Optional[str] = None,
    error_message: Optional[str] = None,
    ai_provider: Optional[str] = None,
    ai_model: Optional[str] = None,
) -> Optional[AuditLog]:
    """
    Catat aksi ke audit log.

    Args:
        db: Database session
        user_id: ID user yang melakukan aksi
        action: Nama aksi (LOGIN, LOGOUT, UPLOAD_DOCUMENT, dll.)
        resource_type: Tipe resource yang diaksi (regulation, document, dll.)
        resource_id: ID resource
        details: Detail aksi (JSON string, tanpa data sensitif)
        ip: IP address
        status: SUCCESS | FAILED | WARNING
        username: Username (untuk referensi historis)
        user_agent: User agent browser
        error_message: Pesan error jika status FAILED
        ai_provider: Provider AI yang digunakan (jika relevan)
        ai_model: Model AI yang digunakan (jika relevan)

    Returns: AuditLog object atau None jika gagal
    """
    try:
        # Sanitasi details — pastikan tidak mengandung data sensitif
        safe_details = _sanitize_details(details)

        audit = AuditLog(
            user_id=user_id,
            username=username,
            action=action[:100],
            resource_type=resource_type[:100] if resource_type else None,
            resource_id=str(resource_id)[:100] if resource_id else None,
            details=safe_details,
            ip_address=ip[:45] if ip else None,
            user_agent=user_agent[:500] if user_agent else None,
            status=status[:20],
            error_message=error_message[:500] if error_message else None,
            ai_provider=ai_provider[:100] if ai_provider else None,
            ai_model=ai_model[:200] if ai_model else None,
        )
        db.add(audit)
        await db.flush()  # Flush tapi jangan commit (ikut commit caller)
        logger.debug(
            f"Audit: {action} by user={user_id} on {resource_type}/{resource_id} [{status}]"
        )
        return audit

    except Exception as e:
        # Audit log tidak boleh mengganggu operasi utama
        logger.error(f"Failed to write audit log: {e}")
        return None


def _sanitize_details(details: Optional[str]) -> Optional[str]:
    """
    Sanitasi detail aksi untuk menghapus data sensitif.
    Jangan simpan password, token, atau isi dokumen.
    """
    if not details:
        return None

    # Jika string JSON, parse dan filter
    if details.startswith("{") or details.startswith("["):
        try:
            data = json.loads(details)
            data = _remove_sensitive_keys(data)
            return json.dumps(data, ensure_ascii=False)[:1000]
        except (json.JSONDecodeError, TypeError):
            pass

    # Truncate
    return details[:1000]


def _remove_sensitive_keys(obj):
    """Hapus key sensitif dari dict/list secara rekursif."""
    sensitive_keys = {
        "password", "hashed_password", "token", "access_token",
        "refresh_token", "api_key", "secret", "private_key",
        "document_text", "full_text", "content",
    }

    if isinstance(obj, dict):
        return {
            k: _remove_sensitive_keys(v)
            for k, v in obj.items()
            if k.lower() not in sensitive_keys
        }
    elif isinstance(obj, list):
        return [_remove_sensitive_keys(item) for item in obj]
    return obj
