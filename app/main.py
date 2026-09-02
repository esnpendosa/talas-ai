"""
TALAS AI — FastAPI Application Entry Point
Telaah Regulasi Berbasis Artificial Intelligence

Prinsip utama:
- AI adalah CO-PILOT ASN, bukan pengambil keputusan hukum.
- Semua output AI wajib diverifikasi manusia.
- Privacy: Default LOCAL ONLY, tidak ada data dikirim ke cloud tanpa izin.
- Semua dokumen diperlakukan sebagai DATA, bukan instruksi AI.
"""
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database.connection import (
    close_database,
    create_all_tables,
    init_database,
)
from app.utils.logging import setup_logging

# ------------------------------------------------------------------ #
# Setup Logging (sebelum import lainnya)
# ------------------------------------------------------------------ #
setup_logging(
    log_dir=settings.LOG_DIR,
    log_level=settings.LOG_LEVEL,
    debug=settings.DEBUG,
)

logger = logging.getLogger("talas_ai.main")


# ------------------------------------------------------------------ #
# Import Models (wajib agar SQLAlchemy mendeteksi tabel)
# ------------------------------------------------------------------ #
import app.models  # noqa: F401 — trigger model registration


# ------------------------------------------------------------------ #
# Import Routers
# ------------------------------------------------------------------ #
from app.api.health import router as health_router
from app.api.auth.router import router as auth_router
from app.api.admin.users import router as admin_users_router
from app.api.regulations.router import router as regulations_router
from app.api.documents.router import router as documents_router
from app.api.ai.router import router as ai_router_endpoint
from app.api.chat.router import router as chat_router
from app.api.analysis.router import router as analysis_router
from app.api.reports.router import router as reports_router
from app.api.dashboard.router import router as dashboard_router
from app.api.admin.audit import router as audit_router
from app.api.admin.backup import router as backup_router


# ------------------------------------------------------------------ #
# Lifespan (startup & shutdown)
# ------------------------------------------------------------------ #
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager aplikasi.
    Startup: inisialisasi database, buat tabel, pastikan direktori ada.
    Shutdown: tutup koneksi database.
    """
    # ---------- STARTUP ----------
    logger.info(f"{'='*60}")
    logger.info(f"  {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"  {settings.APP_TAGLINE}")
    logger.info(f"  Environment: {settings.ENVIRONMENT}")
    logger.info(f"  AI Privacy Mode: {settings.DEFAULT_AI_MODE}")
    logger.info(f"{'='*60}")

    # Buat direktori yang diperlukan
    settings.ensure_directories()
    logger.info("Application directories verified.")

    # Inisialisasi database
    init_database(
        database_url=settings.DATABASE_URL,
        echo=settings.DATABASE_ECHO,
    )

    # Buat semua tabel
    await create_all_tables()
    logger.info("Database tables initialized.")

    # Setup FTS5 search index
    from app.database.connection import get_session_maker
    from app.services.rag.search import ensure_fts_table
    session_factory = get_session_maker()
    async with session_factory() as session:
        await ensure_fts_table(session)

    # Setup AI Router
    from app.services.ai.router import setup_ai_router
    from app.services.ai.provider_registry import sync_providers_from_db
    setup_ai_router(
        privacy_mode=settings.DEFAULT_AI_MODE,
        ollama_url=settings.OLLAMA_BASE_URL if settings.OLLAMA_ENABLED else None,
        ollama_enabled=settings.OLLAMA_ENABLED,
        lmstudio_url=settings.LMSTUDIO_BASE_URL if settings.LMSTUDIO_ENABLED else None,
        lmstudio_enabled=settings.LMSTUDIO_ENABLED,
        cloud_enabled=settings.CLOUD_AI_ENABLED,
        openai_key=settings.OPENAI_API_KEY,
        openai_url=settings.OPENAI_BASE_URL,
    )
    # Sync provider tambahan dari database
    from app.services.ai.router import get_ai_router
    session_factory = get_session_maker()
    async with session_factory() as session:
        await sync_providers_from_db(session, get_ai_router())
        # Load task configs dari database
        from app.models.ai import AITaskConfig
        from sqlalchemy import select as sa_select
        result = await session.execute(
            sa_select(AITaskConfig).where(AITaskConfig.user_id == None)
        )
        for cfg in result.scalars().all():
            if cfg.provider_name and cfg.model_id:
                get_ai_router().set_task_config(
                    task_name=cfg.task_name,
                    provider_name=cfg.provider_name,
                    model_id=cfg.model_id,
                    temperature=cfg.temperature or 0.1,
                    max_tokens=cfg.max_tokens,
                )
    logger.info("AI Router initialized.")

    # Seed database jika first run
    if settings.FIRST_RUN:
        try:
            from scripts.seed import run_seed
            await run_seed()
        except ImportError:
            logger.warning(
                "Seed script not available. Skipping initial data setup."
            )
        except Exception as e:
            logger.warning(f"Seed failed (non-fatal): {e}")

    logger.info(f"TALAS AI started on {settings.HOST}:{settings.PORT}")

    yield  # Aplikasi berjalan

    # ---------- SHUTDOWN ----------
    logger.info("TALAS AI shutting down...")
    await close_database()
    logger.info("Database connection closed. Goodbye.")


# ------------------------------------------------------------------ #
# FastAPI Application
# ------------------------------------------------------------------ #
app = FastAPI(
    title=settings.APP_NAME,
    description=f"""
## {settings.APP_NAME}

{settings.APP_DESCRIPTION}

**Tagline:** {settings.APP_TAGLINE}

---

### ⚠️ PENTING

Semua output AI adalah **TINJAUAN AWAL** yang wajib diverifikasi oleh analis hukum.

AI bukan pengambil keputusan hukum. AI adalah co-pilot ASN.

---

### Privacy Mode

Default: **LOCAL ONLY** — dokumen tidak dikirim ke cloud tanpa izin eksplisit pengguna.
    """,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan,
)


# ------------------------------------------------------------------ #
# Middleware
# ------------------------------------------------------------------ #

# CORS — hanya localhost untuk development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        f"http://{settings.HOST}:{settings.PORT}",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# Trusted hosts — proteksi Host header injection
if settings.is_production:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", settings.HOST],
    )


# ------------------------------------------------------------------ #
# Security Headers Middleware
# ------------------------------------------------------------------ #
@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Tambahkan security headers ke semua response."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # CSP dasar — akan diperketat di phase security
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:;"
    )
    return response


# ------------------------------------------------------------------ #
# Global Exception Handlers
# ------------------------------------------------------------------ #
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handler 404 — jangan tampilkan stack trace."""
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "message": "Endpoint tidak ditemukan.",
            "error_code": "NOT_FOUND",
        },
    )


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    """Handler 500 — jangan tampilkan stack trace ke user."""
    logger.error(f"Internal server error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Terjadi kesalahan internal. Silakan hubungi administrator.",
            "error_code": "INTERNAL_SERVER_ERROR",
        },
    )


# ------------------------------------------------------------------ #
# Static Files & Templates
# ------------------------------------------------------------------ #
import os
static_dir = os.path.join(os.path.dirname(__file__), "static")
templates_dir = os.path.join(os.path.dirname(__file__), "templates")

if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Buat Jinja2Templates dengan auto_reload=False untuk menghindari
# bug LRU cache di Python 3.14 (unhashable dict key)
try:
    from jinja2 import Environment, FileSystemLoader
    _jinja_env = Environment(
        loader=FileSystemLoader(templates_dir),
        auto_reload=False,
        cache_size=0,  # Disable cache — fix Python 3.14 bug
    )
    _jinja_ok = True
except Exception:
    _jinja_ok = False


# ------------------------------------------------------------------ #
# Routers
# ------------------------------------------------------------------ #
app.include_router(health_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(admin_users_router, prefix="/api")
app.include_router(regulations_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(ai_router_endpoint, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(analysis_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(audit_router, prefix="/api")
app.include_router(backup_router, prefix="/api")


# ------------------------------------------------------------------ #
# Root endpoint
# ------------------------------------------------------------------ #
@app.get("/", include_in_schema=False)
async def root(request: Request):
    """
    Root endpoint — serve dashboard HTML.
    Membaca file HTML langsung untuk menghindari Jinja2 cache bug di Python 3.14.
    """
    from fastapi.responses import HTMLResponse

    index_path = os.path.join(templates_dir, "index.html")
    if os.path.exists(index_path):
        try:
            # Baca dan serve HTML langsung — bypass Jinja2 cache bug
            with open(index_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            return HTMLResponse(content=html_content, status_code=200)
        except Exception as e:
            logger.warning(f"HTML serve failed: {e}")

    # Fallback JSON jika file tidak ada
    return JSONResponse({
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": settings.APP_DESCRIPTION,
        "tagline": settings.APP_TAGLINE,
        "status": "running",
        "docs": "/docs" if settings.DEBUG else "disabled",
        "health": "/api/health",
        "privacy_mode": settings.DEFAULT_AI_MODE,
        "disclaimer": (
            "TINJAUAN AWAL AI — WAJIB VERIFIKASI MANUSIA. "
            "AI adalah co-pilot ASN, bukan pengambil keputusan hukum."
        ),
    })
