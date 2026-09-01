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
from fastapi.templating import Jinja2Templates

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
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
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

templates = Jinja2Templates(directory=templates_dir)


# ------------------------------------------------------------------ #
# Routers
# ------------------------------------------------------------------ #
app.include_router(health_router, prefix="/api")

# Placeholder routers (akan diisi di phase selanjutnya)
# app.include_router(auth_router, prefix="/api/auth")
# app.include_router(regulations_router, prefix="/api/regulations")
# app.include_router(documents_router, prefix="/api/documents")
# app.include_router(analysis_router, prefix="/api/analysis")
# app.include_router(chat_router, prefix="/api/chat")
# app.include_router(reports_router, prefix="/api/reports")
# app.include_router(ai_router_endpoint, prefix="/api/ai")
# app.include_router(admin_router, prefix="/api/admin")


# ------------------------------------------------------------------ #
# Root endpoint
# ------------------------------------------------------------------ #
@app.get("/", include_in_schema=False)
async def root(request: Request):
    """
    Root endpoint.
    Jika template index.html ada dan dapat di-render, tampilkan UI.
    Jika tidak, kembalikan JSON info.
    """
    index_template = os.path.join(templates_dir, "index.html")
    if os.path.exists(index_template):
        try:
            return templates.TemplateResponse("index.html", {"request": request})
        except Exception as e:
            logger.warning(f"Template render failed, falling back to JSON: {e}")

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
