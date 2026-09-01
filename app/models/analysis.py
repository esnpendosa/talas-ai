"""
TALAS AI — Analysis Models
Model untuk hasil analisis AI terhadap regulasi/raperbup.
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


class Analysis(Base, TimestampMixin, UUIDMixin):
    """
    Satu sesi analisis AI terhadap sebuah regulasi/raperbup.
    Berisi beberapa AnalysisFinding.
    """
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    regulation_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("regulations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    analysis_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    # Tipe: LEGAL_BASIS | CONFLICT | CONSISTENCY | COMPARISON | FULL

    status: Mapped[str] = mapped_column(
        String(50), default="PENDING", nullable=False, index=True
    )
    # Status: PENDING | PROCESSING | COMPLETED | FAILED

    # Summary statistik
    total_articles: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    found_legal_basis: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    needs_review_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    potential_conflicts: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    inconsistencies: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # AI metadata
    ai_provider: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ai_model: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    ai_privacy_mode: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    findings: Mapped[List["AnalysisFinding"]] = relationship(
        "AnalysisFinding", back_populates="analysis", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_analysis_regulation_id", "regulation_id"),
        Index("ix_analysis_type_status", "analysis_type", "status"),
    )


class AnalysisFinding(Base, TimestampMixin, UUIDMixin):
    """
    Satu temuan analisis AI.
    Setiap finding dapat di-review oleh manusia.
    """
    __tablename__ = "analysis_findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Referensi ke pasal yang dianalisis
    pasal: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ayat: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    finding_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    # Tipe: LEGAL_BASIS | CONFLICT | CONSISTENCY | COMPARISON

    # Hasil AI
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    # FOUND | NOT_FOUND | NEEDS_REVIEW | NO_ISSUE | DIFFERENCE | POTENTIAL_CONFLICT

    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    finding: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    analysis_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommendation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Review manusia
    review_status: Mapped[str] = mapped_column(
        String(50), default="AI_GENERATED", nullable=False, index=True
    )
    # AI_GENERATED | UNDER_REVIEW | VERIFIED | REJECTED | REVISED | FINAL

    reviewed_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reviewer_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    analysis: Mapped["Analysis"] = relationship("Analysis", back_populates="findings")
    sources: Mapped[List["AnalysisSource"]] = relationship(
        "AnalysisSource",
        back_populates="finding",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_finding_analysis_id", "analysis_id"),
        Index("ix_finding_review_status", "review_status"),
        Index("ix_finding_pasal", "pasal"),
    )


class AnalysisSource(Base, TimestampMixin):
    """
    Sumber/evidence yang mendukung sebuah AnalysisFinding.
    Setiap klaim hukum harus dapat dilacak ke sumber.
    """
    __tablename__ = "analysis_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    finding_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("analysis_findings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Citation
    regulation_name: Mapped[str] = mapped_column(String(500), nullable=False)
    regulation_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    regulation_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pasal: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ayat: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    similarity_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    finding: Mapped["AnalysisFinding"] = relationship(
        "AnalysisFinding", back_populates="sources"
    )

    __table_args__ = (
        Index("ix_source_finding_id", "finding_id"),
    )
