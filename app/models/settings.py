"""
TALAS AI — Application Settings Model
Konfigurasi yang disimpan di database (bukan .env).
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base
from app.models.base import TimestampMixin


class AppSettings(Base, TimestampMixin):
    """Pengaturan aplikasi yang dapat diubah dari UI."""
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    value_type: Mapped[str] = mapped_column(
        String(20), default="string", nullable=False
    )
    # Tipe: string | integer | float | boolean | json
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # True = dapat dilihat user biasa, False = admin only

    def __repr__(self) -> str:
        return f"<AppSettings {self.key}={self.value}>"
