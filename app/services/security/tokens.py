"""
TALAS AI — JWT Token Service
Membuat dan memverifikasi access token berbasis JWT.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt

logger = logging.getLogger("talas_ai.security")


def create_access_token(
    subject: str,
    secret_key: str,
    algorithm: str = "HS256",
    expires_minutes: int = 480,
    extra_claims: Optional[dict] = None,
) -> str:
    """Buat JWT access token."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, secret_key, algorithm=algorithm)


def decode_access_token(
    token: str,
    secret_key: str,
    algorithm: str = "HS256",
) -> Optional[dict]:
    """
    Decode dan validasi JWT token.
    Return payload dict atau None jika invalid/expired.
    """
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError as e:
        logger.warning(f"Token decode failed: {type(e).__name__}")
        return None
