"""
TALAS AI — Test Configuration & Fixtures
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import event as sa_event

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Override env untuk testing
os.environ.update({
    "DATABASE_URL": "sqlite:///./data/test_talas.db",
    "ENVIRONMENT": "development",
    "DEBUG": "true",
    "SECRET_KEY": "test-secret-key-for-testing-only-not-production",
    "LOG_LEVEL": "WARNING",
    "DEFAULT_AI_MODE": "local_only",
    "CLOUD_AI_ENABLED": "false",
    "FIRST_RUN": "false",
})


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Fresh in-memory engine per test function — isolasi penuh."""
    from app.database.connection import Base

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

    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Session per test. Tidak menggunakan rollback agar commit benar-benar bekerja."""
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        yield session
        # Tidak rollback — engine dibuang setelah test


@pytest_asyncio.fixture(scope="function")
async def client(test_engine) -> AsyncGenerator[AsyncClient, None]:
    """HTTP test client dengan DB di-override ke test engine."""
    import app.database.connection as db_module

    # Override engine ke test engine
    original_engine = db_module._engine
    original_maker = db_module._async_session_maker

    db_module._engine = test_engine
    db_module._async_session_maker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac

    db_module._engine = original_engine
    db_module._async_session_maker = original_maker
