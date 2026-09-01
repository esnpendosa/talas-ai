"""
TALAS AI — Admin User Management API
CRUD pengguna — hanya untuk ADMIN/superuser.
"""
from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.dependencies import require_superuser
from app.models.user import User, UserRole, Role
from app.schemas.auth import UserCreate, UserMe, UserUpdate
from app.services.security.hashing import hash_password

logger = logging.getLogger("talas_ai.admin")

router = APIRouter(prefix="/admin/users", tags=["Admin — Pengguna"])


@router.get(
    "",
    response_model=List[UserMe],
    summary="Daftar pengguna",
    dependencies=[Depends(require_superuser())],
)
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).order_by(User.id))
    users = result.scalars().all()
    out = []
    for u in users:
        roles_result = await db.execute(
            select(Role.name).join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == u.id)
        )
        roles = [r[0] for r in roles_result.fetchall()]
        out.append(UserMe(
            id=u.id, uuid=u.uuid, username=u.username, email=u.email,
            full_name=u.full_name, position=u.position, department=u.department,
            is_active=u.is_active, is_superuser=u.is_superuser,
            must_change_password=u.must_change_password,
            ai_privacy_mode=u.ai_privacy_mode, roles=roles,
        ))
    return out


@router.post(
    "",
    response_model=UserMe,
    status_code=status.HTTP_201_CREATED,
    summary="Buat pengguna baru",
    dependencies=[Depends(require_superuser())],
)
async def create_user(
    request: Request,
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    # Cek duplikat username
    existing = await db.execute(
        select(User).where(User.username == body.username)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username sudah digunakan.")

    # Cek duplikat email
    existing_email = await db.execute(
        select(User).where(User.email == body.email)
    )
    if existing_email.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email sudah digunakan.")

    user = User(
        username=body.username,
        email=body.email,
        full_name=body.full_name,
        position=body.position,
        department=body.department,
        hashed_password=hash_password(body.password),
        must_change_password=True,
        is_active=True,
    )
    db.add(user)
    await db.flush()

    # Assign role
    role_result = await db.execute(select(Role).where(Role.name == body.role))
    role = role_result.scalar_one_or_none()
    if role:
        db.add(UserRole(user_id=user.id, role_id=role.id))

    await db.commit()

    return UserMe(
        id=user.id, uuid=user.uuid, username=user.username, email=user.email,
        full_name=user.full_name, position=user.position, department=user.department,
        is_active=user.is_active, is_superuser=user.is_superuser,
        must_change_password=user.must_change_password,
        ai_privacy_mode=user.ai_privacy_mode, roles=[body.role],
    )


@router.put(
    "/{user_id}",
    response_model=UserMe,
    summary="Update pengguna",
    dependencies=[Depends(require_superuser())],
)
async def update_user(
    user_id: int,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Pengguna tidak ditemukan.")

    if body.full_name is not None:
        user.full_name = body.full_name
    if body.position is not None:
        user.position = body.position
    if body.department is not None:
        user.department = body.department
    if body.ai_privacy_mode is not None:
        user.ai_privacy_mode = body.ai_privacy_mode
    if body.is_active is not None:
        user.is_active = body.is_active

    await db.commit()

    roles_result = await db.execute(
        select(Role.name).join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id)
    )
    roles = [r[0] for r in roles_result.fetchall()]
    return UserMe(
        id=user.id, uuid=user.uuid, username=user.username, email=user.email,
        full_name=user.full_name, position=user.position, department=user.department,
        is_active=user.is_active, is_superuser=user.is_superuser,
        must_change_password=user.must_change_password,
        ai_privacy_mode=user.ai_privacy_mode, roles=roles,
    )
