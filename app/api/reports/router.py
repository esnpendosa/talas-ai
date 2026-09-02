"""
TALAS AI — Reports API Router (Phase 14)
Endpoints untuk generate dan download laporan.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.dependencies import get_current_user, require_permissions
from app.models.report import Report, ReportVersion
from app.models.user import User

logger = logging.getLogger("talas_ai.api.reports")

router = APIRouter(tags=["reports"])

DISCLAIMER = "TINJAUAN AWAL AI — WAJIB VERIFIKASI MANUSIA."


class GenerateReportRequest(BaseModel):
    analysis_id: int
    format: str = "json"  # docx | pdf | json


@router.post(
    "/reports/generate",
    status_code=status.HTTP_201_CREATED,
    summary="Generate laporan telaah",
)
async def generate_report_endpoint(
    request: GenerateReportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("reports:create")),
):
    """
    Generate laporan telaah regulasi.
    Format: docx | pdf | json (fallback ke json jika lib tidak tersedia).
    """
    from app.services.reports.generator import generate_report

    try:
        result = await generate_report(
            db=db,
            analysis_id=request.analysis_id,
            format=request.format,
            generated_by=current_user.id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Report generation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Gagal generate laporan: {str(e)}",
        )


@router.get(
    "/reports/{report_id}/download",
    summary="Download file laporan",
)
async def download_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("reports:read")),
):
    """Download file laporan yang sudah digenerate."""
    # Ambil report
    result = await db.execute(
        select(Report).where(Report.id == report_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Laporan tidak ditemukan.")

    # Ambil versi terkini
    result = await db.execute(
        select(ReportVersion)
        .where(ReportVersion.report_id == report_id)
        .where(ReportVersion.is_current == True)  # noqa: E712
        .order_by(ReportVersion.version_number.desc())
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="File laporan tidak ditemukan.")

    file_path = Path(version.file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="File laporan tidak ditemukan di disk.",
        )

    # Content type berdasarkan format
    media_types = {
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "pdf": "application/pdf",
        "json": "application/json",
    }
    media_type = media_types.get(version.file_format, "application/octet-stream")

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=file_path.name,
        headers={
            "X-Disclaimer": DISCLAIMER,
        },
    )


@router.get(
    "/reports",
    summary="Daftar laporan",
)
async def list_reports(
    analysis_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("reports:read")),
):
    """Daftar laporan yang sudah digenerate."""
    stmt = select(Report)
    if analysis_id:
        stmt = stmt.where(Report.analysis_id == analysis_id)

    result = await db.execute(stmt)
    reports = result.scalars().all()

    return {
        "total": len(reports),
        "disclaimer": DISCLAIMER,
        "reports": [
            {
                "id": r.id,
                "analysis_id": r.analysis_id,
                "regulation_id": r.regulation_id,
                "title": r.title,
                "report_type": r.report_type,
                "status": r.status,
            }
            for r in reports
        ],
    }
