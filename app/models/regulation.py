"""
TALAS AI — Regulation Models
Model untuk perpustakaan regulasi.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base
from app.models.base import TimestampMixin, UUIDMixin


class Regulation(Base, TimestampMixin, UUIDMixin):
    """
    Regulasi — UU, PP, Perpres, Permen, Permendagri, Perda, Pergub, Perbup, dll.
    Termasuk Raperbup (Rancangan Peraturan Bupati).
    """
    __tablename__ = "regulations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Identitas regulasi
    jenis: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    # Contoh: UU, PP, Perpres, Permen, Permendagri, Perda, Pergub, Perbup, Raperbup
    nomor: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tahun: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    judul: Mapped[str] = mapped_column(Text, nullable=False)
    singkatan: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Tanggal
    tanggal_penetapan: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    tanggal_berlaku: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Status regulasi
    status: Mapped[str] = mapped_column(
        String(50), default="BERLAKU", nullable=False, index=True
    )
    # Status: BERLAKU | DICABUT | DIUBAH | SEBAGIAN_BERLAKU | TIDAK_DIKETAHUI

    # Sumber
    sumber_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    sumber_file: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True
    )  # SHA256

    # Metadata tambahan
    catatan: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_draft: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # True = Raperbup/Draft, False = regulasi resmi

    # Hierarki
    level: Mapped[int] = mapped_column(
        Integer, default=10, nullable=False, index=True
    )
    # 1=UU, 2=PP, 3=Perpres, 4=Permen, 5=Permendagri, 6=Perda, 7=Pergub, 8=Perbup, 9=Raperbup

    # Tracking
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    documents: Mapped[List["Document"]] = relationship(
        "Document", back_populates="regulation", cascade="all, delete-orphan"
    )
    relationships_from: Mapped[List["RegulationRelationship"]] = relationship(
        "RegulationRelationship",
        foreign_keys="[RegulationRelationship.regulation_id]",
        back_populates="regulation",
        cascade="all, delete-orphan",
    )
    relationships_to: Mapped[List["RegulationRelationship"]] = relationship(
        "RegulationRelationship",
        foreign_keys="[RegulationRelationship.related_regulation_id]",
        back_populates="related_regulation",
    )
    versions: Mapped[List["RegulationVersion"]] = relationship(
        "RegulationVersion", back_populates="regulation", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_regulation_jenis_tahun", "jenis", "tahun"),
        Index("ix_regulation_status", "status"),
        Index("ix_regulation_is_draft", "is_draft"),
    )

    def __repr__(self) -> str:
        return f"<Regulation {self.jenis} No.{self.nomor} Tahun {self.tahun}>"


class RegulationRelationship(Base, TimestampMixin):
    """Relasi antar regulasi (mencabut, mengubah, melaksanakan, dll.)."""
    __tablename__ = "regulation_relationships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    regulation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("regulations.id", ondelete="CASCADE"), nullable=False
    )
    related_regulation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("regulations.id", ondelete="CASCADE"), nullable=False
    )
    relationship_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    # Tipe: MENCABUT | MENGUBAH | MELAKSANAKAN | MERUJUK | DIUBAH_OLEH | DICABUT_OLEH

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    regulation: Mapped["Regulation"] = relationship(
        "Regulation",
        foreign_keys=[regulation_id],
        back_populates="relationships_from",
    )
    related_regulation: Mapped["Regulation"] = relationship(
        "Regulation",
        foreign_keys=[related_regulation_id],
        back_populates="relationships_to",
    )

    __table_args__ = (
        UniqueConstraint(
            "regulation_id",
            "related_regulation_id",
            "relationship_type",
            name="uq_regulation_relationship",
        ),
    )


class RegulationVersion(Base, TimestampMixin):
    """Riwayat versi regulasi."""
    __tablename__ = "regulation_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    regulation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("regulations.id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    changed_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    change_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Snapshot data dalam format JSON string
    snapshot_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    regulation: Mapped["Regulation"] = relationship(
        "Regulation", back_populates="versions"
    )

    __table_args__ = (
        UniqueConstraint(
            "regulation_id", "version_number", name="uq_regulation_version"
        ),
        Index("ix_regulation_version_regulation_id", "regulation_id"),
    )
