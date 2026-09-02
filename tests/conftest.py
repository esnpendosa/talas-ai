"""
TALAS AI — Test Configuration & Fixtures
Menggunakan session-scoped engine dengan function-scoped cleanup.
"""
from __future__ import annotations

import asyncio
import os
import sys
import typing
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import event as sa_event, text

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

# ------------------------------------------------------------------ #
# FIX: Patch SQLAlchemy untuk Python 3.14 compatibility
# Python 3.14 mengubah cara Union.__getitem__ bekerja.
# Patch ini harus dilakukan SEBELUM import SQLAlchemy models.
# ------------------------------------------------------------------ #
def _patch_sqlalchemy_for_python314():
    """
    Patch sqlalchemy.util.typing.make_union_type untuk Python 3.14.
    Di Python 3.14, typing.Union.__getitem__((str, None)) tidak bekerja lagi.
    Gunakan types.UnionType atau typing.Union[str, None] langsung.
    """
    import sys
    if sys.version_info < (3, 14):
        return  # Tidak perlu patch untuk Python < 3.14

    try:
        import sqlalchemy.util.typing as sa_typing

        def patched_make_union_type(*types):
            """Patched version yang kompatibel dengan Python 3.14."""
            if len(types) == 1 and isinstance(types[0], tuple):
                types = types[0]
            # Gunakan typing.Optional untuk 2 tipe, Union untuk lebih
            non_none = [t for t in types if t is not type(None)]
            has_none = type(None) in types
            if not non_none:
                return type(None)
            if len(non_none) == 1 and has_none:
                return typing.Optional[non_none[0]]
            result = non_none[0]
            for t in non_none[1:]:
                result = typing.Union[result, t]
            if has_none:
                result = typing.Optional[result]
            return result

        sa_typing.make_union_type = patched_make_union_type
    except (ImportError, AttributeError):
        pass  # Jika tidak bisa patch, lanjutkan


# Terapkan patch sebelum import apapun dari SQLAlchemy
_patch_sqlalchemy_for_python314()

# Override env untuk testing
os.environ.update({
    "DATABASE_URL": "sqlite:///./data/test_talas.db",
    "ENVIRONMENT": "development",
    "DEBUG": "false",
    "SECRET_KEY": "test-secret-key-for-testing-only-not-production",
    "LOG_LEVEL": "WARNING",
    "DEFAULT_AI_MODE": "local_only",
    "CLOUD_AI_ENABLED": "false",
    "FIRST_RUN": "false",
})


# ------------------------------------------------------------------ #
# Event loop — satu per session
# ------------------------------------------------------------------ #
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ------------------------------------------------------------------ #
# Database engine — satu per session, shared semua tests
# ------------------------------------------------------------------ #
@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """
    Satu in-memory engine untuk seluruh session test.
    Tabel dibuat sekali, data di-rollback per test.
    """
    from app.database.connection import Base
    import app.models  # noqa: F401 — register semua model

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )

    def set_pragmas(dbapi_conn, conn_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    sa_event.listen(engine.sync_engine, "connect", set_pragmas)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


# ------------------------------------------------------------------ #
# Session factory — session scope
# ------------------------------------------------------------------ #
@pytest_asyncio.fixture(scope="session")
async def session_factory(test_engine):
    """Session maker yang shared untuk seluruh test session."""
    return async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


# ------------------------------------------------------------------ #
# DB Session — function scope, cleanup setelah tiap test
# ------------------------------------------------------------------ #
@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine, session_factory) -> AsyncGenerator[AsyncSession, None]:
    """
    Session per test function.
    Data yang diinsert akan dibersihkan setelah test selesai.
    """
    async with session_factory() as session:
        yield session
        # Cleanup: rollback dulu, lalu truncate semua tabel
        await session.rollback()

    # Truncate semua tabel setelah setiap test
    await _truncate_all_tables(test_engine)


async def _truncate_all_tables(engine) -> None:
    """Hapus semua data dari semua tabel (tanpa drop tabel)."""
    from app.database.connection import Base
    # Urutan terbalik untuk menghindari FK constraint
    table_names = list(reversed([
        t.name for t in Base.metadata.sorted_tables
    ]))
    async with engine.begin() as conn:
        # Disable FK sementara untuk truncate
        await conn.execute(text("PRAGMA foreign_keys=OFF"))
        for table in table_names:
            try:
                await conn.execute(text(f"DELETE FROM {table}"))
            except Exception:
                pass  # Skip jika tabel tidak ada (FTS virtual table, dll.)
        await conn.execute(text("PRAGMA foreign_keys=ON"))


# ------------------------------------------------------------------ #
# HTTP Test Client — function scope
# ------------------------------------------------------------------ #
@pytest_asyncio.fixture(scope="function")
async def client(test_engine, session_factory) -> AsyncGenerator[AsyncClient, None]:
    """HTTP test client dengan DB di-override ke test engine."""
    import app.database.connection as db_module

    original_engine = db_module._engine
    original_maker = db_module._async_session_maker

    db_module._engine = test_engine
    db_module._async_session_maker = session_factory

    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac

    db_module._engine = original_engine
    db_module._async_session_maker = original_maker
