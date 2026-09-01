"""
TALAS AI — Chat Models
Model untuk sesi chatbot "Tanya Regulasi".
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import (
    Boolean,
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


class ChatSession(Base, TimestampMixin, UUIDMixin):
    """Sesi percakapan chatbot."""
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    ai_provider: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ai_model: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    ai_privacy_mode: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Jika sesi terkait dengan regulasi tertentu
    regulation_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("regulations.id", ondelete="SET NULL"),
        nullable=True,
    )

    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_chat_session_user_id", "user_id"),
    )


class ChatMessage(Base, TimestampMixin):
    """Satu pesan dalam sesi chatbot."""
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: Mapped[str] = mapped_column(String(20), nullable=False)
    # role: "user" | "assistant" | "system"

    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Metadata AI response
    ai_provider: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ai_model: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sources_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # sources disimpan sebagai JSON string

    has_warning: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    warning_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Apakah response sudah diverifikasi?
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    session: Mapped["ChatSession"] = relationship(
        "ChatSession", back_populates="messages"
    )

    __table_args__ = (
        Index("ix_chat_message_session_id", "session_id"),
        Index("ix_chat_message_role", "role"),
    )
