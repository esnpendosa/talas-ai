"""
TALAS AI — Report Models
Model untuk laporan telaah regulasi.
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base
from app.models.base import TimestampMixin, UUIDMixin


class Report(Base, TimestampMixin, UUIDMixin):
    """Laporan telaah regulasi yang dihasilkan."""
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    regulation_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("regulations.id", ondelete="CASCADE"),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    report_type: Mapped[str] = mapped_column(
        String(50), default="TELAAH", nullable=False
    )
    # Tipe: TELAAH | SUMMARY | COMPARISON

    status: Mapped[str] = mapped_column(
        String(50), default="DRAFT", nullable=False, index=True
    )
    # Status: DRAFT | FINAL | ARCHIVED

    generated_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    versions: Mapped[List["ReportVersion"]] = relationship(
        "ReportVersion", back_populates="report", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_report_analysis_id", "analysis_id"),
        Index("ix_report_status", "status"),
    )


class ReportVersion(Base, TimestampMixin):
    """Versi file laporan yang dihasilkan."""
    __tablename__ = "report_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    file_format: Mapped[str] = mapped_column(String(10), nullable=False)  # docx, pdf
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    generated_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    report: Mapped["Report"] = relationship("Report", back_populates="versions")

    __table_args__ = (
        Index("ix_report_version_report_id", "report_id"),
    )
