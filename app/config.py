"""
TALAS AI — Application Configuration
Semua konfigurasi dibaca dari environment variables / .env file
Tidak ada hardcoded secrets
"""
import os
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Konfigurasi utama aplikasi TALAS AI.
    Semua nilai dibaca dari environment variables atau .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------ #
    # Application
    # ------------------------------------------------------------------ #
    APP_NAME: str = "TALAS AI"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Telaah Regulasi Berbasis Artificial Intelligence"
    APP_TAGLINE: str = "AI sebagai Co-Pilot ASN untuk Telaah Regulasi"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True

    # Secret key — WAJIB diganti di production
    SECRET_KEY: str = "change-this-in-production"

    # ------------------------------------------------------------------ #
    # Server
    # ------------------------------------------------------------------ #
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    WORKERS: int = 1

    # ------------------------------------------------------------------ #
    # Database
    # ------------------------------------------------------------------ #
    DATABASE_URL: str = "sqlite:///./data/talas.db"
    DATABASE_ECHO: bool = False

    # ------------------------------------------------------------------ #
    # Security / Auth
    # ------------------------------------------------------------------ #
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480       # 8 jam
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    BCRYPT_ROUNDS: int = 12

    # ------------------------------------------------------------------ #
    # File Storage
    # ------------------------------------------------------------------ #
    UPLOAD_DIR: str = "./data/documents"
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: str = "pdf,docx,doc"
    BACKUP_DIR: str = "./data/backups"
    INDEX_DIR: str = "./data/indexes"
    EXPORT_DIR: str = "./data/exports"
    MAX_BACKUPS: int = 10

    # ------------------------------------------------------------------ #
    # Logging
    # ------------------------------------------------------------------ #
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "./logs"

    # ------------------------------------------------------------------ #
    # AI Privacy Mode
    # ------------------------------------------------------------------ #
    DEFAULT_AI_MODE: Literal["local_only", "cloud_allowed", "ask_before_sending"] = (
        "local_only"
    )

    # ------------------------------------------------------------------ #
    # Local AI Providers
    # ------------------------------------------------------------------ #
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_TIMEOUT: int = 120
    OLLAMA_ENABLED: bool = True

    LMSTUDIO_BASE_URL: str = "http://localhost:1234"
    LMSTUDIO_TIMEOUT: int = 120
    LMSTUDIO_ENABLED: bool = False

    LLAMACPP_BASE_URL: str = ""
    LLAMACPP_ENABLED: bool = False

    # ------------------------------------------------------------------ #
    # Cloud AI (disabled by default)
    # ------------------------------------------------------------------ #
    CLOUD_AI_ENABLED: bool = False
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"

    # ------------------------------------------------------------------ #
    # Default Models (dapat dioverride per user)
    # ------------------------------------------------------------------ #
    DEFAULT_CHAT_MODEL: str = ""
    DEFAULT_EMBEDDING_MODEL: str = ""
    DEFAULT_LEGAL_BASIS_MODEL: str = ""
    DEFAULT_CONFLICT_MODEL: str = ""
    DEFAULT_CONSISTENCY_MODEL: str = ""

    # ------------------------------------------------------------------ #
    # RAG Settings
    # ------------------------------------------------------------------ #
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64
    MAX_RETRIEVAL_RESULTS: int = 10
    MIN_SIMILARITY_SCORE: float = 0.3

    # ------------------------------------------------------------------ #
    # Feature Flags
    # ------------------------------------------------------------------ #
    ENABLE_OCR: bool = True
    ENABLE_SEMANTIC_SEARCH: bool = True
    ENABLE_AUDIT_LOG: bool = True
    FIRST_RUN: bool = True

    # ------------------------------------------------------------------ #
    # Computed Properties
    # ------------------------------------------------------------------ #
    @property
    def allowed_extensions_list(self) -> list[str]:
        """Daftar ekstensi file yang diizinkan."""
        return [ext.strip().lower() for ext in self.ALLOWED_EXTENSIONS.split(",")]

    @property
    def max_upload_bytes(self) -> int:
        """Ukuran maksimal upload dalam bytes."""
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def database_path(self) -> Path:
        """Path absolut ke database SQLite."""
        url = self.DATABASE_URL.replace("sqlite:///", "")
        return Path(url).resolve()

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if len(v) < 16:
            raise ValueError("SECRET_KEY must be at least 16 characters long.")
        return v

    def ensure_directories(self) -> None:
        """Buat direktori yang diperlukan jika belum ada."""
        dirs = [
            self.UPLOAD_DIR,
            self.BACKUP_DIR,
            self.INDEX_DIR,
            self.EXPORT_DIR,
            self.LOG_DIR,
            "./data",
        ]
        for d in dirs:
            Path(d).mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Singleton settings.
    Gunakan dependency injection FastAPI:
        settings: Settings = Depends(get_settings)
    Atau import langsung:
        from app.config import get_settings
        settings = get_settings()
    """
    return Settings()


# Instance global untuk kemudahan import
settings = get_settings()
