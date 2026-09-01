"""
TALAS AI — Test Configuration & Fixtures
Pytest configuration untuk seluruh test suite.
"""
import asyncio
import os
import sys
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Tambahkan root ke Python path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Gunakan database in-memory untuk testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Override environment variables untuk testing
os.environ["DATABASE_URL"] = "sqlite:///./data/test_talas.db"
os.environ["ENVIRONMENT"] = "development"
os.environ["DEBUG"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only-not-production"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["DEFAULT_AI_MODE"] = "local_only"
os.environ["CLOUD_AI_ENABLED"] = "false"
os.environ["FIRST_RUN"] = "false"


# ------------------------------------------------------------------ #
# Async Event Loop
# ------------------------------------------------------------------ #
@pytest.fixture(scope="session")
def event_loop():
    """Buat event loop untuk seluruh test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ------------------------------------------------------------------ #
# Database Fixtures
# ------------------------------------------------------------------ #
@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Buat test database engine (in-memory SQLite)."""
    from sqlalchemy import event as sa_event
    from app.database.connection import Base

    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )

    # Aktifkan WAL dan foreign keys
    def set_pragmas(dbapi_conn, conn_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    sa_event.listen(engine.sync_engine, "connect", set_pragmas)

    # Import semua model agar terdaftar
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Berikan database session per test function.
    Setiap test dimulai dengan transaction bersih dan di-rollback setelah selesai.
    """
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


# ------------------------------------------------------------------ #
# HTTP Client Fixtures
# ------------------------------------------------------------------ #
@pytest_asyncio.fixture(scope="function")
async def client(test_engine, db_session) -> AsyncGenerator[AsyncClient, None]:
    """
    HTTP client untuk test API endpoints.
    Database di-override ke test database.
    """
    from app.main import app
    from app.database.connection import get_db, _async_session_maker
    import app.database.connection as db_module

    # Override session maker ke test session
    original_session_maker = db_module._async_session_maker
    db_module._async_session_maker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    db_module._engine = test_engine

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac

    db_module._async_session_maker = original_session_maker


# ------------------------------------------------------------------ #
# Helper Fixtures
# ------------------------------------------------------------------ #
@pytest_asyncio.fixture
async def seeded_db(db_session):
    """Database dengan data seed untuk testing."""
    from app.database.connection import _async_session_maker
    import app.database.connection as db_module

    # Override session maker untuk seed
    original = db_module._async_session_maker

    class MockSessionMaker:
        def __call__(self):
            return db_session

        def __enter__(self):
            return db_session

        def __exit__(self, *args):
            pass

    db_module._async_session_maker = lambda: _context_session(db_session)

    from scripts.seed import run_seed
    await run_seed(force=True)

    db_module._async_session_maker = original
    yield db_session


async def _context_session(session):
    """Context manager wrapper untuk session."""
    class _CM:
        async def __aenter__(self):
            return session
        async def __aexit__(self, *args):
            pass
    return _CM()
