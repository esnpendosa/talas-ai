"""
TALAS AI — Database Connection
SQLite + SQLAlchemy async engine.
WAL mode diaktifkan untuk performa baca-tulis lebih baik.
Foreign keys diaktifkan secara eksplisit (SQLite default: off).
"""
import logging
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger("talas_ai.database")


class Base(DeclarativeBase):
    """
    Base class untuk semua SQLAlchemy model.
    Digunakan sebagai parent class semua tabel.
    """
    pass


# Engine dan SessionMaker — diinisialisasi oleh init_database()
_engine = None
_async_session_maker = None


def _sqlite_pragmas(dbapi_connection, connection_record):
    """
    Aktifkan WAL mode dan foreign keys setiap kali koneksi dibuka.
    Ini diperlukan karena SQLite per-connection settings.
    """
    cursor = dbapi_connection.cursor()
    # WAL mode: lebih baik untuk concurrent read/write
    cursor.execute("PRAGMA journal_mode=WAL")
    # Foreign key enforcement
    cursor.execute("PRAGMA foreign_keys=ON")
    # Synchronous NORMAL: balance antara safety dan performa
    cursor.execute("PRAGMA synchronous=NORMAL")
    # Cache size: 64 MB
    cursor.execute("PRAGMA cache_size=-65536")
    cursor.close()


def init_database(database_url: str, echo: bool = False):
    """
    Inisialisasi engine dan session factory.
    Dipanggil satu kali saat startup aplikasi.
    """
    global _engine, _async_session_maker

    # Pastikan direktori database ada
    if "sqlite" in database_url:
        db_path_str = database_url.replace("sqlite+aiosqlite:///", "").replace(
            "sqlite:///", ""
        )
        db_path = Path(db_path_str)
        db_path.parent.mkdir(parents=True, exist_ok=True)

    # Konversi URL ke async jika perlu
    async_url = database_url
    if database_url.startswith("sqlite:///") and "aiosqlite" not in database_url:
        async_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///")

    logger.info(f"Initializing database: {async_url}")

    _engine = create_async_engine(
        async_url,
        echo=echo,
        # SQLite spesifik: batasi 1 koneksi per waktu untuk WAL
        connect_args={"check_same_thread": False},
    )

    # Daftarkan PRAGMA hook
    event.listen(_engine.sync_engine, "connect", _sqlite_pragmas)

    _async_session_maker = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    logger.info("Database engine initialized successfully.")
    return _engine


def get_engine():
    """Dapatkan engine yang sudah diinisialisasi."""
    if _engine is None:
        raise RuntimeError(
            "Database engine belum diinisialisasi. "
            "Panggil init_database() terlebih dahulu."
        )
    return _engine


def get_session_maker():
    """Dapatkan session maker yang sudah diinisialisasi."""
    if _async_session_maker is None:
        raise RuntimeError(
            "Session maker belum diinisialisasi. "
            "Panggil init_database() terlebih dahulu."
        )
    return _async_session_maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency untuk mendapatkan database session.
    Otomatis commit/rollback dan tutup session.

    Penggunaan:
        @router.get("/example")
        async def example(db: AsyncSession = Depends(get_db)):
            ...
    """
    session_factory = get_session_maker()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_all_tables() -> None:
    """Buat semua tabel yang terdaftar di Base.metadata."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("All database tables created/verified.")


async def check_database_health() -> dict:
    """
    Periksa koneksi dan integritas database.
    Digunakan oleh health check endpoint.
    """
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            # Test query sederhana
            result = await conn.execute(text("SELECT 1"))
            result.fetchone()

            # Cek tabel yang ada
            tables_result = await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            )
            tables = [row[0] for row in tables_result.fetchall()]

            # Cek WAL mode
            wal_result = await conn.execute(text("PRAGMA journal_mode"))
            journal_mode = wal_result.fetchone()[0]

            # Cek integrity (ringan)
            integrity_result = await conn.execute(text("PRAGMA integrity_check(1)"))
            integrity = integrity_result.fetchone()[0]

        return {
            "status": "healthy",
            "tables_count": len(tables),
            "tables": tables,
            "journal_mode": journal_mode,
            "integrity": integrity,
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
        }


async def close_database() -> None:
    """Tutup koneksi database saat shutdown."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        logger.info("Database connection closed.")
