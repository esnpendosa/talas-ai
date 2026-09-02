"""
TALAS AI — AI Provider & Model Configuration Models
Konfigurasi multi-provider AI yang tersimpan di database.
API key disimpan terenkripsi — TIDAK pernah dikembalikan ke client.
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
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base
from app.models.base import TimestampMixin


class AIProvider(Base, TimestampMixin):
    """
    Konfigurasi provider AI yang disimpan di database.
    Provider dapat ditambah, diedit, dihapus melalui UI/API.
    API key disimpan terenkripsi — tidak pernah dikembalikan plaintext ke client.
    """
    __tablename__ = "ai_providers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Tipe: ollama | lmstudio | llamacpp | openai | anthropic | google |
    #        openrouter | groq | together | mistral | cohere | custom | mock

    base_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    timeout: Mapped[int] = mapped_column(Integer, default=120, nullable=False)

    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_cloud: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requires_api_key: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # API key disimpan sebagai teks terenkripsi (base64 XOR sederhana)
    # Bukan enkripsi production-grade, tapi mencegah exposure langsung
    # Untuk keamanan lebih tinggi, gunakan secret manager eksternal
    api_key_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    api_key_hint: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # 4 karakter terakhir untuk konfirmasi

    # Header tambahan (JSON string) — untuk custom auth
    extra_headers_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status terakhir
    last_health_check: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    last_health_check_at: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Metadata
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Urutan tampilan
    sort_order: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

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
    display_name: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    model_type: Mapped[str] = mapped_column(String(50), default="chat", nullable=False)
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
    """Konfigurasi model AI per task — global (user_id=NULL) atau per user."""
    __tablename__ = "ai_task_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    task_name: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    model_id: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        Index("ix_ai_task_config_user_task", "user_id", "task_name"),
    )


class AIUsageLog(Base, TimestampMixin):
    """Log penggunaan AI."""
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
    """Log fallback antar provider."""
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
    was_cloud_fallback: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        Index("ix_ai_fallback_original_provider", "original_provider"),
    )
