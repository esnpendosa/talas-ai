"""
TALAS AI — Review Models
Model untuk human review terhadap finding AI.
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base
from app.models.base import TimestampMixin, UUIDMixin


class Review(Base, TimestampMixin, UUIDMixin):
    """Review manusia terhadap AnalysisFinding."""
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    finding_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("analysis_findings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    action: Mapped[str] = mapped_column(String(50), nullable=False)
    # action: TERIMA | TOLAK | EDIT | KOMENTAR | VERIFIKASI

    revised_finding: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    revised_recommendation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    comments: Mapped[List["ReviewComment"]] = relationship(
        "ReviewComment", back_populates="review", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_review_finding_id", "finding_id"),
        Index("ix_review_reviewer_id", "reviewer_id"),
    )


class ReviewComment(Base, TimestampMixin):
    """Komentar pada sebuah review."""
    __tablename__ = "review_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    review_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    review: Mapped["Review"] = relationship("Review", back_populates="comments")
