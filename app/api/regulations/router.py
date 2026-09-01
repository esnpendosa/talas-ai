"""
TALAS AI — Regulations API Router
CRUD perpustakaan regulasi.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.dependencies import get_current_user, require_permissions
from app.models.regulation import Regulation
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.regulation import (
    RegulationCreate,
    RegulationList,
    RegulationOut,
    RegulationUpdate,
    LEVEL_MAP,
    RegulationSearchResult,
)

logger = logging.getLogger("talas_ai.regulations")

router = APIRouter(prefix="/regulations", tags=["Regulasi"])


@router.get(
    "",
    response_model=PaginatedResponse[RegulationList],
    summary="Daftar regulasi",
    dependencies=[Depends(require_permissions("regulations:read"))],
)
async def list_regulations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    jenis: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    tahun: Optional[int] = Query(None),
    is_draft: Optional[bool] = Query(None),
    search: Optional[str] = Query(None, description="Cari di judul dan nomor"),
    db: AsyncSession = Depends(get_db),
):
    query = select(Regulation).order_by(Regulation.level, Regulation.tahun.desc())

    if jenis:
        query = query.where(Regulation.jenis == jenis)
    if status:
        query = query.where(Regulation.status == status)
    if tahun:
        query = query.where(Regulation.tahun == tahun)
    if is_draft is not None:
        query = query.where(Regulation.is_draft == is_draft)
    if search:
        term = f"%{search}%"
        query = query.where(
            or_(Regulation.judul.ilike(term), Regulation.nomor.ilike(term))
        )

    # Count
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar_one()

    # Paginate
    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    items = result.scalars().all()
    total_pages = (total + page_size - 1) // page_size

    return PaginatedResponse(
        data=[RegulationList.model_validate(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "",
    response_model=RegulationOut,
    status_code=status.HTTP_201_CREATED,
    summary="Tambah regulasi",
    dependencies=[Depends(require_permissions("regulations:write"))],
)
async def create_regulation(
    request: Request,
    body: RegulationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    reg = Regulation(
        **body.model_dump(),
        level=LEVEL_MAP.get(body.jenis, 10),
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(reg)
    await db.commit()
    await db.refresh(reg)
    await _audit(db, current_user.id, "CREATE_REGULATION", str(reg.id))
    return RegulationOut.model_validate(reg)


@router.get(
    "/{regulation_id}",
    response_model=RegulationOut,
    summary="Detail regulasi",
    dependencies=[Depends(require_permissions("regulations:read"))],
)
async def get_regulation(
    regulation_id: int,
    db: AsyncSession = Depends(get_db),
):
    reg = await _get_or_404(db, regulation_id)
    return RegulationOut.model_validate(reg)


@router.put(
    "/{regulation_id}",
    response_model=RegulationOut,
    summary="Update regulasi",
    dependencies=[Depends(require_permissions("regulations:write"))],
)
async def update_regulation(
    regulation_id: int,
    body: RegulationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    reg = await _get_or_404(db, regulation_id)

    update_data = body.model_dump(exclude_none=True)
    if "jenis" in update_data:
        update_data["level"] = LEVEL_MAP.get(update_data["jenis"], 10)

    for key, value in update_data.items():
        setattr(reg, key, value)
    reg.updated_by = current_user.id

    await db.commit()
    await db.refresh(reg)
    await _audit(db, current_user.id, "UPDATE_REGULATION", str(regulation_id))
    return RegulationOut.model_validate(reg)


@router.delete(
    "/{regulation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Hapus regulasi",
    dependencies=[Depends(require_permissions("regulations:delete"))],
)
async def delete_regulation(
    regulation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    reg = await _get_or_404(db, regulation_id)
    await _audit(db, current_user.id, "DELETE_REGULATION", str(regulation_id))
    await db.delete(reg)
    await db.commit()


@router.get(
    "/search/keyword",
    response_model=List[RegulationSearchResult],
    summary="Cari regulasi (keyword)",
    dependencies=[Depends(require_permissions("regulations:read"))],
)
async def search_regulations(
    q: str = Query(..., min_length=2, description="Kata kunci pencarian"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Keyword search sederhana pada judul, nomor, dan catatan."""
    term = f"%{q}%"
    result = await db.execute(
        select(Regulation)
        .where(
            or_(
                Regulation.judul.ilike(term),
                Regulation.nomor.ilike(term),
                Regulation.catatan.ilike(term),
            )
        )
        .order_by(Regulation.level, Regulation.tahun.desc())
        .limit(limit)
    )
    regs = result.scalars().all()
    return [
        RegulationSearchResult(
            id=r.id, uuid=r.uuid, jenis=r.jenis, nomor=r.nomor,
            tahun=r.tahun, judul=r.judul, status=r.status,
        )
        for r in regs
    ]


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

async def _get_or_404(db: AsyncSession, regulation_id: int) -> Regulation:
    result = await db.execute(
        select(Regulation).where(Regulation.id == regulation_id)
    )
    reg = result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="Regulasi tidak ditemukan.")
    return reg


async def _audit(db, user_id, action, resource_id):
    from app.models.audit import AuditLog
    db.add(AuditLog(
        user_id=user_id, action=action,
        resource_type="regulation", resource_id=resource_id,
        status="SUCCESS",
    ))
    await db.commit()
