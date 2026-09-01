"""
TALAS AI — Authentication Service
Login, session, RBAC permission check.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User, UserRole, Role, RolePermission, Permission
from app.services.security.hashing import verify_password, needs_rehash, hash_password
from app.services.security.tokens import create_access_token, decode_access_token
from app.config import settings

logger = logging.getLogger("talas_ai.security")

# Jumlah maksimal gagal login sebelum akun dikunci (5 menit)
MAX_FAILED_ATTEMPTS = 5


async def authenticate_user(
    db: AsyncSession, username: str, password: str
) -> Optional[User]:
    """
    Autentikasi user berdasarkan username dan password.
    Catat failed attempts. Kembalikan User jika berhasil, None jika gagal.
    JANGAN log password dalam kondisi apapun.
    """
    result = await db.execute(
        select(User).where(User.username == username.strip().lower())
    )
    user = result.scalar_one_or_none()

    if user is None:
        # Tetap jalankan hash check untuk cegah timing attack
        verify_password("dummy", "$argon2id$v=19$m=65536,t=2,p=2$dummy$dummy")
        logger.warning(f"Login attempt for unknown username: {username}")
        return None

    if not user.is_active:
        logger.warning(f"Login attempt on inactive account: {username}")
        return None

    # Cek apakah akun terkunci
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        logger.warning(f"Login attempt on locked account: {username}")
        return None

    if not verify_password(password, user.hashed_password):
        user.failed_login_count += 1
        if user.failed_login_count >= MAX_FAILED_ATTEMPTS:
            from datetime import timedelta
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=5)
            logger.warning(
                f"Account locked due to failed attempts: {username}"
            )
        await db.commit()
        return None

    # Login berhasil — reset counters
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login = datetime.now(timezone.utc)

    # Rehash jika parameter berubah
    if needs_rehash(user.hashed_password):
        user.hashed_password = hash_password(password)

    await db.commit()
    return user


async def get_user_roles(db: AsyncSession, user_id: int) -> List[str]:
    """Ambil daftar nama role milik user."""
    result = await db.execute(
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
    )
    return [row[0] for row in result.fetchall()]


async def get_user_permissions(db: AsyncSession, user_id: int) -> List[str]:
    """
    Ambil daftar permission milik user dalam format 'resource:action'.
    Format ini konsisten meski nama permission punya suffix.
    """
    from app.models.user import Permission, RolePermission, Role, UserRole
    result = await db.execute(
        select(Permission.resource, Permission.action)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
        .distinct()
    )
    return [f"{row[0]}:{row[1]}" for row in result.fetchall()]


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    result = await db.execute(
        select(User).where(User.username == username.strip().lower())
    )
    return result.scalar_one_or_none()


def create_token_for_user(user: User, roles: List[str]) -> dict:
    """Buat access token untuk user yang sudah terauthentikasi."""
    token = create_access_token(
        subject=str(user.id),
        secret_key=settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
        expires_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        extra_claims={
            "username": user.username,
            "is_superuser": user.is_superuser,
            "roles": roles,
        },
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


async def verify_token_and_get_user(
    db: AsyncSession, token: str
) -> Optional[User]:
    """Verifikasi token JWT dan kembalikan user."""
    payload = decode_access_token(
        token, settings.SECRET_KEY, settings.ALGORITHM
    )
    if not payload:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    return await get_user_by_id(db, int(user_id))
