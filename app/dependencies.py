"""
TALAS AI — FastAPI Dependencies
Dependency injection untuk route handlers: DB session, current user, RBAC.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database.connection import get_db
from app.models.user import User

logger = logging.getLogger("talas_ai.security")

# Bearer token extractor
_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency: dapatkan user dari Bearer token.
    Raise 401 jika token tidak valid.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token autentikasi diperlukan.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    from app.services.security.auth import verify_token_and_get_user

    user = await verify_token_and_get_user(db, credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak valid atau sudah kedaluwarsa.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun tidak aktif.",
        )
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency: pastikan user aktif."""
    return current_user


def require_permissions(*permissions: str):
    """
    Dependency factory: pastikan user memiliki semua permission yang disebutkan.
    Contoh:
        @router.get("/x", dependencies=[Depends(require_permissions("regulations:read"))])
    """
    async def _check(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if current_user.is_superuser:
            return current_user

        from app.services.security.auth import get_user_permissions
        user_perms = await get_user_permissions(db, current_user.id)
        user_perm_set = set(user_perms)

        for perm in permissions:
            if perm not in user_perm_set:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Akses ditolak. Permission diperlukan: {perm}",
                )
        return current_user

    return _check


def require_roles(*roles: str):
    """
    Dependency factory: pastikan user memiliki salah satu role yang disebutkan.
    """
    async def _check(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if current_user.is_superuser:
            return current_user

        from app.services.security.auth import get_user_roles
        user_roles = await get_user_roles(db, current_user.id)
        if not any(r in user_roles for r in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Akses ditolak. Role tidak memiliki izin untuk aksi ini.",
            )
        return current_user

    return _check


def require_superuser():
    """Dependency: hanya superuser/admin yang dapat mengakses."""
    async def _check(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Akses ditolak. Hanya administrator.",
            )
        return current_user
    return _check
