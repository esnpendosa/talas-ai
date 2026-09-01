"""
TALAS AI — AI Provider & Model Configuration Models
Konfigurasi multi-provider AI yang tersimpan di database.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base
from app.models.base import TimestampMixin


class AIProvider(Base, TimestampMixin):
    """Konfigurasi provider AI (Ollama, LM Studio, llama.cpp, Cloud, dll.)."""
    __tablename__ = "ai_providers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    provider_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    # Tipe: ollama | lmstudio | llamacpp | openai_compatible | cloud | mock

    base_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    timeout: Mapped[int] = mapped_column(Integer, default=120, nullable=False)

    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_cloud: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requires_api_key: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # API key TIDAK disimpan di sini — dibaca dari env/user input

    last_health_check: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )
    # Status: connected | disconnected | error | unknown
    last_health_check_at: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<AIProvider {self.name} [{self.provider_type}]>"


class AIModel(Base, TimestampMixin):
    """Model AI yang tersedia dari sebuah provider."""
    __tablename__ = "ai_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ai_providers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_id: Mapped[str] = mapped_column(String(300), nullable=False)
    # model_id = identifier yang digunakan provider (misal: "llama3.2:3b")
    display_name: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    model_type: Mapped[str] = mapped_column(
        String(50), default="chat", nullable=False
    )
    # Tipe: chat | embedding | completion

    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    context_length: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    size_gb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    __table_args__ = (
        Index("ix_ai_model_provider_id", "provider_id"),
        Index("ix_ai_model_type", "model_type"),
    )

    def __repr__(self) -> str:
        return f"<AIModel {self.model_id}>"


class AITaskConfig(Base, TimestampMixin):
    """Konfigurasi model AI per task per user."""
    __tablename__ = "ai_task_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    # Jika user_id NULL = default global

    task_name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Task: chat | legal_basis | conflict | consistency | comparison | summary | report | embedding

    provider_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    model_id: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        Index("ix_ai_task_config_user_task", "user_id", "task_name"),
    )


class AIUsageLog(Base, TimestampMixin):
    """Log penggunaan AI untuk monitoring."""
    __tablename__ = "ai_usage_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    provider_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_id: Mapped[str] = mapped_column(String(300), nullable=False)
    task_name: Mapped[str] = mapped_column(String(100), nullable=False)

    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_cloud: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="success", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        Index("ix_ai_usage_provider_model", "provider_name", "model_id"),
        Index("ix_ai_usage_task", "task_name"),
    )


class AIFallbackLog(Base, TimestampMixin):
    """Log fallback dari satu provider ke provider lainnya."""
    __tablename__ = "ai_fallback_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    original_provider: Mapped[str] = mapped_column(String(100), nullable=False)
    original_model: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    fallback_provider: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    fallback_model: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    task_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    was_cloud_fallback: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    __table_args__ = (
        Index("ix_ai_fallback_original_provider", "original_provider"),
    )
