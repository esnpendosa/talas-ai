"""
TALAS AI — Logging Configuration
Menggunakan Python standard logging dengan format terstruktur.
Log dipisah per kategori: application, ai, security, audit.
PENTING: Jangan pernah log password, API key, atau isi dokumen rahasia.
"""
import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional


# Format standar
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _get_file_handler(
    log_path: Path,
    level: int,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
) -> logging.handlers.RotatingFileHandler:
    """Buat rotating file handler."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        filename=str(log_path),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
    return handler


def setup_logging(
    log_dir: str = "./logs",
    log_level: str = "INFO",
    debug: bool = False,
) -> None:
    """
    Setup logging untuk seluruh aplikasi.
    Dipanggil satu kali saat startup.
    """
    level = logging.DEBUG if debug else getattr(logging, log_level.upper(), logging.INFO)
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(
        logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    )

    # Hindari duplikasi handler jika setup_logging dipanggil ulang
    if not root_logger.handlers:
        root_logger.addHandler(console_handler)
    else:
        # Reset dan tambah ulang
        root_logger.handlers.clear()
        root_logger.addHandler(console_handler)

    # Application log
    app_logger = logging.getLogger("talas_ai")
    app_logger.addHandler(
        _get_file_handler(log_path / "application.log", level)
    )

    # AI log — khusus untuk aktivitas AI/LLM
    ai_logger = logging.getLogger("talas_ai.ai")
    ai_logger.addHandler(
        _get_file_handler(log_path / "ai.log", level)
    )

    # Security log — login, auth, access control
    security_logger = logging.getLogger("talas_ai.security")
    security_logger.addHandler(
        _get_file_handler(log_path / "security.log", logging.WARNING)
    )

    # Audit log — perubahan data, aksi pengguna
    audit_logger = logging.getLogger("talas_ai.audit")
    audit_logger.addHandler(
        _get_file_handler(log_path / "audit.log", logging.INFO)
    )

    # Kurangi noise dari library pihak ketiga
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if debug else logging.WARNING
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Dapatkan logger dengan namespace talas_ai.
    Contoh: get_logger("database") → logger "talas_ai.database"
    """
    if not name.startswith("talas_ai"):
        name = f"talas_ai.{name}"
    return logging.getLogger(name)
