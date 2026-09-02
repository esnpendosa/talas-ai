"""
TALAS AI — Analysis API Router (Phase 9-13)
Endpoints untuk analisis regulasi: legal basis, konflik, konsistensi, perbandingan.
Juga human review endpoint.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.dependencies import get_current_user, require_permissions
from app.models.analysis import Analysis, AnalysisFinding
from app.models.review import Review
from app.models.user import User

logger = logging.getLogger("talas_ai.api.analysis")

router = APIRouter(tags=["analysis"])

DISCLAIMER = "TINJAUAN AWAL AI — WAJIB VERIFIKASI MANUSIA."


# ------------------------------------------------------------------ #
# Request / Response Schemas
# ------------------------------------------------------------------ #

class StartAnalysisRequest(BaseModel):
    regulation_id: int
    analysis_type: str = Field(
        default="FULL",
        description="LEGAL_BASIS | CONFLICT | CONSISTENCY | FULL",
    )


class CompareRegulationsRequest(BaseModel):
    regulation_id_a: int
    regulation_id_b: int


class ReviewFindingRequest(BaseModel):
    action: str = Field(
        description="TERIMA | TOLAK | EDIT | KOMENTAR | VERIFIKASI"
    )
    revised_finding: Optional[str] = None
    revised_recommendation: Optional[str] = None
    notes: Optional[str] = None


class AnalysisSummaryResponse(BaseModel):
    id: int
    regulation_id: int
    analysis_type: str
    status: str
    total_articles: Optional[int]
    found_legal_basis: Optional[int]
    needs_review_count: Optional[int]
    potential_conflicts: Optional[int]
    inconsistencies: Optional[int]
    ai_provider: Optional[str]
    ai_model: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    disclaimer: str = DISCLAIMER

    class Config:
        from_attributes = True


class FindingResponse(BaseModel):
    id: int
    analysis_id: int
    pasal: Optional[str]
    ayat: Optional[str]
    finding_type: str
    status: str
    confidence: Optional[float]
    finding: Optional[str]
    analysis_text: Optional[str]
    recommendation: Optional[str]
    review_status: str
    disclaimer: str = DISCLAIMER

    class Config:
        from_attributes = True


# ------------------------------------------------------------------ #
# POST /api/analysis — Mulai analisis
# ------------------------------------------------------------------ #

@router.post(
    "/analysis",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Mulai analisis regulasi",
)
async def start_analysis(
    request: StartAnalysisRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("analysis:create")),
):
    """
    Mulai analisis AI terhadap regulasi.
    Analisis berjalan secara asinkron (background).
    """
    # Validasi tipe analisis
    valid_types = {"LEGAL_BASIS", "CONFLICT", "CONSISTENCY", "FULL"}
    if request.analysis_type not in valid_types:
        raise HTTPException(
            status_code=422,
            detail=f"analysis_type harus salah satu dari: {valid_types}",
        )

    # Buat record Analysis
    analysis = Analysis(
        regulation_id=request.regulation_id,
        analysis_type=request.analysis_type,
        status="PENDING",
        created_by=current_user.id,
        started_at=datetime.now(timezone.utc),
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    # Jalankan analisis secara langsung (synchronous untuk MVP)
    try:
        analysis.status = "PROCESSING"
        await db.commit()

        finding_count = 0

        if request.analysis_type in ("LEGAL_BASIS", "FULL"):
            from app.services.analysis.legal_basis import check_legal_basis
            count = await check_legal_basis(db, request.regulation_id, analysis.id)
            analysis.found_legal_basis = count
            finding_count += count

        if request.analysis_type in ("CONFLICT", "FULL"):
            from app.services.analysis.conflict import check_conflicts
            count = await check_conflicts(db, request.regulation_id, analysis.id)
            analysis.potential_conflicts = count
            finding_count += count

        if request.analysis_type in ("CONSISTENCY", "FULL"):
            from app.services.analysis.consistency import check_consistency
            count = await check_consistency(db, request.regulation_id, analysis.id)
            analysis.inconsistencies = count
            finding_count += count

        analysis.total_articles = finding_count
        analysis.status = "COMPLETED"
        analysis.completed_at = datetime.now(timezone.utc)
        await db.commit()

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        analysis.status = "FAILED"
        analysis.error_message = str(e)[:500]
        await db.commit()

    return {
        "success": True,
        "message": "Analisis selesai.",
        "analysis_id": analysis.id,
        "status": analysis.status,
        "disclaimer": DISCLAIMER,
    }


# ------------------------------------------------------------------ #
# GET /api/analysis/{id} — Status analisis
# ------------------------------------------------------------------ #

@router.get(
    "/analysis/{analysis_id}",
    response_model=AnalysisSummaryResponse,
    summary="Status dan ringkasan analisis",
)
async def get_analysis(
    analysis_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("analysis:read")),
):
    result = await db.execute(
        select(Analysis).where(Analysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analisis tidak ditemukan.")

    return AnalysisSummaryResponse(
        id=analysis.id,
        regulation_id=analysis.regulation_id,
        analysis_type=analysis.analysis_type,
        status=analysis.status,
        total_articles=analysis.total_articles,
        found_legal_basis=analysis.found_legal_basis,
        needs_review_count=analysis.needs_review_count,
        potential_conflicts=analysis.potential_conflicts,
        inconsistencies=analysis.inconsistencies,
        ai_provider=analysis.ai_provider,
        ai_model=analysis.ai_model,
        started_at=analysis.started_at,
        completed_at=analysis.completed_at,
        error_message=analysis.error_message,
    )


# ------------------------------------------------------------------ #
# GET /api/analysis/{id}/findings — Daftar findings
# ------------------------------------------------------------------ #

@router.get(
    "/analysis/{analysis_id}/findings",
    summary="Daftar temuan analisis",
)
async def list_findings(
    analysis_id: int,
    finding_type: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("analysis:read")),
):
    stmt = select(AnalysisFinding).where(AnalysisFinding.analysis_id == analysis_id)
    if finding_type:
        stmt = stmt.where(AnalysisFinding.finding_type == finding_type)
    if status:
        stmt = stmt.where(AnalysisFinding.status == status)

    result = await db.execute(stmt)
    findings = result.scalars().all()

    return {
        "analysis_id": analysis_id,
        "total": len(findings),
        "disclaimer": DISCLAIMER,
        "findings": [
            FindingResponse(
                id=f.id,
                analysis_id=f.analysis_id,
                pasal=f.pasal,
                ayat=f.ayat,
                finding_type=f.finding_type,
                status=f.status,
                confidence=f.confidence,
                finding=f.finding,
                analysis_text=f.analysis_text,
                recommendation=f.recommendation,
                review_status=f.review_status,
            )
            for f in findings
        ],
    }


# ------------------------------------------------------------------ #
# POST /api/findings/{finding_id}/review — Human review
# ------------------------------------------------------------------ #

@router.post(
    "/findings/{finding_id}/review",
    summary="Submit human review terhadap temuan AI",
)
async def review_finding(
    finding_id: int,
    request: ReviewFindingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("review:create")),
):
    """
    Submit human review terhadap temuan AI.

    Aksi:
    - TERIMA: set review_status = VERIFIED
    - TOLAK: set review_status = REJECTED
    - EDIT: update teks finding, set review_status = REVISED
    - KOMENTAR: tambah catatan, pertahankan review_status
    - VERIFIKASI: set review_status = VERIFIED (aksi formal)
    """
    valid_actions = {"TERIMA", "TOLAK", "EDIT", "KOMENTAR", "VERIFIKASI"}
    if request.action not in valid_actions:
        raise HTTPException(
            status_code=422,
            detail=f"action harus salah satu dari: {valid_actions}",
        )

    # Ambil finding
    result = await db.execute(
        select(AnalysisFinding).where(AnalysisFinding.id == finding_id)
    )
    finding = result.scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=404, detail="Temuan tidak ditemukan.")

    # AI tidak dapat mengubah VERIFIED findings
    if finding.review_status == "VERIFIED" and not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="Temuan yang sudah VERIFIED tidak dapat diubah. Buat versi baru jika diperlukan.",
        )

    # Buat record Review
    review = Review(
        finding_id=finding_id,
        reviewer_id=current_user.id,
        action=request.action,
        revised_finding=request.revised_finding,
        revised_recommendation=request.revised_recommendation,
        notes=request.notes,
    )
    db.add(review)

    # Update finding berdasarkan aksi
    if request.action in ("TERIMA", "VERIFIKASI"):
        finding.review_status = "VERIFIED"
        finding.reviewed_by = current_user.id
        finding.reviewed_at = datetime.now(timezone.utc)
        if request.notes:
            finding.reviewer_notes = request.notes

    elif request.action == "TOLAK":
        finding.review_status = "REJECTED"
        finding.reviewed_by = current_user.id
        finding.reviewed_at = datetime.now(timezone.utc)
        if request.notes:
            finding.reviewer_notes = request.notes

    elif request.action == "EDIT":
        finding.review_status = "REVISED"
        finding.reviewed_by = current_user.id
        finding.reviewed_at = datetime.now(timezone.utc)
        if request.revised_finding:
            finding.finding = request.revised_finding
        if request.revised_recommendation:
            finding.recommendation = request.revised_recommendation
        if request.notes:
            finding.reviewer_notes = request.notes

    elif request.action == "KOMENTAR":
        finding.review_status = "UNDER_REVIEW"
        if request.notes:
            existing = finding.reviewer_notes or ""
            finding.reviewer_notes = (existing + "\n" + request.notes).strip()

    # Log audit
    try:
        from app.services.security.audit_service import log_action
        await log_action(
            db=db,
            user_id=current_user.id,
            action=f"REVIEW_{request.action}",
            resource_type="finding",
            resource_id=str(finding_id),
            details=f"action={request.action}, new_status={finding.review_status}",
            ip=None,
            status="SUCCESS",
        )
    except Exception:
        pass  # Audit log non-fatal

    await db.commit()

    return {
        "success": True,
        "finding_id": finding_id,
        "action": request.action,
        "new_review_status": finding.review_status,
        "message": f"Review berhasil. Status temuan: {finding.review_status}",
        "disclaimer": DISCLAIMER,
    }


# ------------------------------------------------------------------ #
# POST /api/analysis/compare — Perbandingan dua regulasi
# ------------------------------------------------------------------ #

@router.post(
    "/analysis/compare",
    summary="Bandingkan dua regulasi pasal per pasal",
)
async def compare_regulations_endpoint(
    request: CompareRegulationsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("analysis:read")),
):
    """
    Bandingkan dua regulasi secara pasal per pasal.
    Kategori: UNCHANGED | CHANGED | ADDED | REMOVED | NEEDS_REVIEW
    """
    from app.services.analysis.comparison import compare_regulations
    result = await compare_regulations(
        db,
        request.regulation_id_a,
        request.regulation_id_b,
    )
    return result
