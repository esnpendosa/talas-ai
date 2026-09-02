"""
TALAS AI — Dashboard API Router (Phase 15)
Endpoint untuk statistik dashboard.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.dependencies import get_current_user
from app.models.analysis import Analysis, AnalysisFinding
from app.models.regulation import Regulation
from app.models.user import User

logger = logging.getLogger("talas_ai.api.dashboard")

router = APIRouter(tags=["dashboard"])

DISCLAIMER = "TINJAUAN AWAL AI — WAJIB VERIFIKASI MANUSIA."


@router.get(
    "/dashboard/stats",
    summary="Statistik dashboard",
)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Kembalikan statistik untuk dashboard utama.

    Returns:
        total_regulasi: total semua regulasi
        total_raperbup: total rancangan peraturan (is_draft=True)
        telaah_selesai: analisis dengan status COMPLETED
        perlu_review: findings dengan review_status AI_GENERATED
        potensi_konflik: findings POTENTIAL_CONFLICT
        ketidakkonsistenan: findings DIFFERENCE dari CONSISTENCY
    """
    # Total regulasi
    result = await db.execute(
        select(func.count(Regulation.id))
    )
    total_regulasi = result.scalar_one() or 0

    # Total raperbup (draft)
    result = await db.execute(
        select(func.count(Regulation.id)).where(Regulation.is_draft == True)  # noqa: E712
    )
    total_raperbup = result.scalar_one() or 0

    # Telaah selesai
    result = await db.execute(
        select(func.count(Analysis.id)).where(Analysis.status == "COMPLETED")
    )
    telaah_selesai = result.scalar_one() or 0

    # Perlu review (findings AI_GENERATED yang belum direview)
    result = await db.execute(
        select(func.count(AnalysisFinding.id))
        .where(AnalysisFinding.review_status == "AI_GENERATED")
    )
    perlu_review = result.scalar_one() or 0

    # Potensi konflik
    result = await db.execute(
        select(func.count(AnalysisFinding.id))
        .where(AnalysisFinding.status == "POTENTIAL_CONFLICT")
    )
    potensi_konflik = result.scalar_one() or 0

    # Ketidakkonsistenan (DIFFERENCE dari CONSISTENCY)
    result = await db.execute(
        select(func.count(AnalysisFinding.id))
        .where(AnalysisFinding.finding_type == "CONSISTENCY")
        .where(AnalysisFinding.status == "DIFFERENCE")
    )
    ketidakkonsistenan = result.scalar_one() or 0

    return {
        "total_regulasi": total_regulasi,
        "total_raperbup": total_raperbup,
        "telaah_selesai": telaah_selesai,
        "perlu_review": perlu_review,
        "potensi_konflik": potensi_konflik,
        "ketidakkonsistenan": ketidakkonsistenan,
        "disclaimer": DISCLAIMER,
    }
