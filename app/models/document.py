"""
TALAS AI — Document Models
Model untuk dokumen yang diupload dan hasil ekstraksi teks.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base
from app.models.base import TimestampMixin, UUIDMixin


class Document(Base, TimestampMixin, UUIDMixin):
    """Dokumen yang diupload ke sistem (PDF, DOCX, dll.)."""
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    regulation_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("regulations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # File info
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True
    )
    # stored_filename menggunakan UUID-safe name, bukan original
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # bytes
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)  # pdf, docx
    file_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )  # SHA256

    # Processing status
    processing_status: Mapped[str] = mapped_column(
        String(50), default="PENDING", nullable=False, index=True
    )
    # Status: PENDING | PROCESSING | COMPLETED | FAILED | DUPLICATE

    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    extracted_text_length: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ocr_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    processing_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Metadata
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    uploaded_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    regulation: Mapped[Optional["Regulation"]] = relationship(
        "Regulation", back_populates="documents"
    )
    chunks: Mapped[List["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan"
    )
    metadata_items: Mapped[List["DocumentMetadata"]] = relationship(
        "DocumentMetadata", back_populates="document", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_document_processing_status", "processing_status"),
        Index("ix_document_regulation_id", "regulation_id"),
    )

    def __repr__(self) -> str:
        return f"<Document {self.original_filename} [{self.processing_status}]>"


class DocumentChunk(Base, TimestampMixin):
    """
    Potongan teks dokumen untuk RAG (Retrieval-Augmented Generation).
    Setiap chunk adalah unit pencarian.
    """
    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )

    # Konten
    text: Mapped[str] = mapped_column(Text, nullable=False)
    text_length: Mapped[int] = mapped_column(Integer, nullable=False)

    # Posisi dalam dokumen
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    page_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Struktur regulasi (jika terdeteksi)
    bab: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    bagian: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    pasal: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ayat: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Vector embedding (disimpan sebagai BLOB/base64 jika diperlukan)
    embedding_model: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    has_embedding: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")

    __table_args__ = (
        Index("ix_chunk_document_id", "document_id"),
        Index("ix_chunk_pasal", "pasal"),
        Index("ix_chunk_has_embedding", "has_embedding"),
    )


class DocumentMetadata(Base, TimestampMixin):
    """Metadata tambahan dokumen dalam format key-value."""
    __tablename__ = "document_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    document: Mapped["Document"] = relationship(
        "Document", back_populates="metadata_items"
    )

    __table_args__ = (
        Index("ix_doc_metadata_document_id", "document_id"),
        Index("ix_doc_metadata_key", "key"),
    )
