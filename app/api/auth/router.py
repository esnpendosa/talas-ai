"""
TALAS AI — Auth API Router
Endpoints: login, logout, me, change-password.
"""
from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    TokenResponse,
    UserMe,
)
from app.services.security.auth import (
    authenticate_user,
    create_token_for_user,
    get_user_roles,
)
from app.services.security.hashing import hash_password

logger = logging.getLogger("talas_ai.security")

router = APIRouter(prefix="/auth", tags=["Autentikasi"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login",
    description="Login dengan username dan password. Mengembalikan Bearer token.",
)
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Login endpoint.
    Rate limiting dan audit log diterapkan.
    Password TIDAK di-log dalam kondisi apapun.
    """
    user = await authenticate_user(db, body.username, body.password)

    if not user:
        # Audit log gagal login
        await _write_audit(
            db,
            user_id=None,
            username=body.username,
            action="LOGIN_FAILED",
            ip=_get_ip(request),
            status="FAILED",
            error="Invalid credentials or account locked",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username atau password salah, atau akun dikunci.",
        )

    roles = await get_user_roles(db, user.id)
    token_data = create_token_for_user(user, roles)

    # Audit log sukses
    await _write_audit(
        db,
        user_id=user.id,
        username=user.username,
        action="LOGIN_SUCCESS",
        ip=_get_ip(request),
        status="SUCCESS",
    )

    logger.info(f"Login success: {user.username}")
    return TokenResponse(**token_data)


@router.post(
    "/logout",
    summary="Logout",
    description="Logout (invalidasi token di sisi client).",
)
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Logout endpoint.
    JWT stateless — client wajib menghapus token.
    Audit log dicatat.
    """
    await _write_audit(
        db,
        user_id=current_user.id,
        username=current_user.username,
        action="LOGOUT",
        ip=_get_ip(request),
        status="SUCCESS",
    )
    return {"message": "Logout berhasil. Hapus token dari client."}


@router.get(
    "/me",
    response_model=UserMe,
    summary="Profil saya",
    description="Dapatkan data profil user yang sedang login.",
)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    roles = await get_user_roles(db, current_user.id)
    return UserMe(
        id=current_user.id,
        uuid=current_user.uuid,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        position=current_user.position,
        department=current_user.department,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        must_change_password=current_user.must_change_password,
        ai_privacy_mode=current_user.ai_privacy_mode,
        roles=roles,
    )


@router.post(
    "/change-password",
    summary="Ganti password",
    description="Ganti password user yang sedang login.",
)
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.security.hashing import verify_password

    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password saat ini tidak benar.",
        )

    current_user.hashed_password = hash_password(body.new_password)
    current_user.must_change_password = False
    await db.commit()

    await _write_audit(
        db,
        user_id=current_user.id,
        username=current_user.username,
        action="CHANGE_PASSWORD",
        ip=_get_ip(request),
        status="SUCCESS",
    )

    return {"message": "Password berhasil diubah."}


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _get_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def _write_audit(
    db: AsyncSession,
    action: str,
    status: str,
    user_id=None,
    username: str = "",
    ip: str = "",
    error: str = "",
):
    from app.models.audit import AuditLog
    log = AuditLog(
        user_id=user_id,
        username=username,
        action=action,
        ip_address=ip,
        resource_type="auth",
        status=status,
        error_message=error or None,
    )
    db.add(log)
    await db.commit()
