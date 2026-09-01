"""
TALAS AI — Password Hashing Service
Menggunakan Argon2 (primary) dengan fallback ke bcrypt.
TIDAK PERNAH menyimpan atau log password plaintext.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("talas_ai.security")


def _get_argon2_hasher():
    from argon2 import PasswordHasher
    return PasswordHasher(
        time_cost=2,
        memory_cost=65536,
        parallelism=2,
        hash_len=32,
        salt_len=16,
    )


def hash_password(password: str) -> str:
    """Hash password menggunakan Argon2. Jangan log hasilnya."""
    try:
        ph = _get_argon2_hasher()
        return ph.hash(password)
    except Exception:
        # Fallback ke bcrypt
        from passlib.context import CryptContext
        ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return ctx.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifikasi password tanpa timing attack."""
    try:
        ph = _get_argon2_hasher()
        return ph.verify(hashed_password, plain_password)
    except Exception:
        try:
            from passlib.context import CryptContext
            ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
            return ctx.verify(plain_password, hashed_password)
        except Exception:
            return False


def needs_rehash(hashed_password: str) -> bool:
    """Cek apakah hash perlu di-update ke parameter terbaru."""
    try:
        ph = _get_argon2_hasher()
        return ph.check_needs_rehash(hashed_password)
    except Exception:
        return False
