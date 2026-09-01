"""
TALAS AI — Audit Log Model
Catat semua aksi penting pengguna.
PENTING: Jangan menyimpan password, API key, atau isi dokumen penuh di sini.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base
from app.models.base import TimestampMixin


class AuditLog(Base, TimestampMixin):
    """Audit trail semua aksi pengguna dan sistem."""
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Siapa
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # Simpan username untuk referensi historis jika user dihapus

    # Apa
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # Contoh: LOGIN, LOGOUT, UPLOAD_DOCUMENT, RUN_ANALYSIS, REVIEW_FINDING

    # Target
    resource_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # resource_id sebagai string untuk fleksibilitas (int atau UUID)

    # Detail
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # JSON string berisi detail aksi — TANPA data sensitif

    # Konteks
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # AI context
    ai_provider: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ai_model: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Hasil
    status: Mapped[str] = mapped_column(
        String(20), default="SUCCESS", nullable=False
    )
    # SUCCESS | FAILED | WARNING

    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        Index("ix_audit_log_user_id", "user_id"),
        Index("ix_audit_log_action", "action"),
        Index("ix_audit_log_created_at", "created_at"),
        Index("ix_audit_log_resource", "resource_type", "resource_id"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} by {self.username}>"
