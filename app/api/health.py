"""
TALAS AI — Health Check Endpoints
Endpoint untuk memeriksa status aplikasi dan komponen.
"""
from datetime import datetime, timezone

from fastapi import APIRouter

from app.config import settings
from app.database.connection import check_database_health
from app.schemas.common import HealthCheck

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthCheck,
    summary="Health Check",
    description="Periksa status aplikasi TALAS AI.",
)
async def health_check():
    """
    Endpoint health check.
    Memeriksa:
    - Status aplikasi
    - Koneksi database
    - Konfigurasi dasar
    """
    db_health = await check_database_health()

    overall_status = "healthy" if db_health.get("status") == "healthy" else "degraded"

    return HealthCheck(
        status=overall_status,
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        database=db_health,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get(
    "/ping",
    summary="Ping",
    description="Cek apakah server berjalan.",
)
async def ping():
    """Endpoint sederhana untuk cek apakah server aktif."""
    return {
        "ping": "pong",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
