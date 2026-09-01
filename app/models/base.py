"""
TALAS AI — Base Model Mixin
Field umum yang digunakan semua model.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column


def utc_now() -> datetime:
    """Waktu sekarang dalam UTC."""
    return datetime.now(timezone.utc)


class TimestampMixin:
    """Mixin untuk kolom created_at dan updated_at."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
        nullable=False,
    )


class UUIDMixin:
    """Mixin untuk UUID sebagai identifier publik."""

    uuid: Mapped[str] = mapped_column(
        String(36),
        default=lambda: str(uuid.uuid4()),
        unique=True,
        nullable=False,
        index=True,
    )
