"""
TALAS AI — Audit Log API (Phase 16)
Endpoints untuk melihat audit log. Hanya admin.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.dependencies import require_superuser
from app.models.audit import AuditLog
from app.models.user import User

logger = logging.getLogger("talas_ai.api.audit")

router = APIRouter(tags=["admin", "audit"])


@router.get(
    "/audit-logs",
    summary="Daftar audit log (admin only)",
)
async def list_audit_logs(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    action: Optional[str] = Query(default=None),
    user_id: Optional[int] = Query(default=None),
    date_from: Optional[str] = Query(default=None, description="Format: YYYY-MM-DD"),
    date_to: Optional[str] = Query(default=None, description="Format: YYYY-MM-DD"),
    resource_type: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_superuser()),
):
    """
    Daftar audit log dengan filter dan pagination.
    Hanya administrator yang dapat mengakses.
    """
    filters = []

    if action:
        filters.append(AuditLog.action.ilike(f"%{action}%"))
    if user_id:
        filters.append(AuditLog.user_id == user_id)
    if resource_type:
        filters.append(AuditLog.resource_type == resource_type)
    if status:
        filters.append(AuditLog.status == status)

    if date_from:
        try:
            dt_from = datetime.strptime(date_from, "%Y-%m-%d")
            filters.append(AuditLog.created_at >= dt_from)
        except ValueError:
            pass

    if date_to:
        try:
            dt_to = datetime.strptime(date_to, "%Y-%m-%d")
            filters.append(AuditLog.created_at <= dt_to)
        except ValueError:
            pass

    stmt = (
        select(AuditLog)
        .where(and_(*filters) if filters else True)
        .order_by(AuditLog.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )

    result = await db.execute(stmt)
    logs = result.scalars().all()

    return {
        "page": page,
        "per_page": per_page,
        "total": len(logs),
        "logs": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "username": log.username,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "details": log.details,
                "ip_address": log.ip_address,
                "status": log.status,
                "error_message": log.error_message,
                "created_at": str(log.created_at) if log.created_at else None,
            }
            for log in logs
        ],
    }
