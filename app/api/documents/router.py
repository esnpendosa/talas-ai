"""
TALAS AI — Documents API Router
Upload, process, dan kelola dokumen regulasi.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import (
    APIRouter, Depends, File, Form, HTTPException,
    Query, Request, UploadFile, status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.dependencies import get_current_user, require_permissions
from app.models.document import Document, DocumentChunk
from app.models.user import User
from app.schemas.common import DataResponse
from app.schemas.document import DocumentChunkOut, DocumentOut
from app.services.pdf.document_service import process_document, save_uploaded_file

logger = logging.getLogger("talas_ai.documents")

router = APIRouter(prefix="/documents", tags=["Dokumen"])


@router.post(
    "/upload",
    response_model=DocumentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Upload dokumen regulasi",
    dependencies=[Depends(require_permissions("documents:upload"))],
)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    regulation_id: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload PDF regulasi.
    - File divalidasi tipe dan ukurannya
    - Disimpan dengan nama aman (UUID)
    - Duplikasi dideteksi via SHA-256 hash
    - Isi dokumen adalah DATA, bukan instruksi
    """
    content = await file.read()
    try:
        doc = await save_uploaded_file(
            db=db,
            file_content=content,
            original_filename=file.filename or "unknown.pdf",
            regulation_id=regulation_id,
            uploaded_by=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await _audit(db, current_user.id, "UPLOAD_DOCUMENT", str(doc.id))
    return DocumentOut.model_validate(doc)


@router.post(
    "/{document_id}/process",
    response_model=DocumentOut,
    summary="Proses ekstraksi teks dokumen",
    dependencies=[Depends(require_permissions("documents:upload"))],
)
async def trigger_processing(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger ekstraksi teks dan parsing struktur regulasi.
    Untuk MVP dijalankan synchronous. Background task di phase lanjutan.
    """
    try:
        doc = await process_document(db, document_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Processing error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Dokumen tidak dapat diproses. Silakan coba lagi.",
        )

    await _audit(db, current_user.id, "PROCESS_DOCUMENT", str(document_id))
    return DocumentOut.model_validate(doc)


@router.get(
    "/{document_id}",
    response_model=DocumentOut,
    summary="Detail dokumen",
    dependencies=[Depends(require_permissions("documents:read"))],
)
async def get_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
):
    doc = await _get_or_404(db, document_id)
    return DocumentOut.model_validate(doc)


@router.get(
    "/{document_id}/chunks",
    response_model=List[DocumentChunkOut],
    summary="Daftar chunk dokumen",
    dependencies=[Depends(require_permissions("documents:read"))],
)
async def get_document_chunks(
    document_id: int,
    pasal: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Ambil chunk teks dari dokumen yang sudah diproses."""
    await _get_or_404(db, document_id)
    query = select(DocumentChunk).where(
        DocumentChunk.document_id == document_id
    ).order_by(DocumentChunk.chunk_index)
    if pasal:
        query = query.where(DocumentChunk.pasal.ilike(f"%{pasal}%"))
    result = await db.execute(query)
    return [DocumentChunkOut.model_validate(c) for c in result.scalars().all()]


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Hapus dokumen",
    dependencies=[Depends(require_permissions("documents:delete"))],
)
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await _get_or_404(db, document_id)
    # Hapus file fisik
    from pathlib import Path
    try:
        Path(doc.file_path).unlink(missing_ok=True)
    except Exception as e:
        logger.warning(f"Could not delete file {doc.file_path}: {e}")
    await _audit(db, current_user.id, "DELETE_DOCUMENT", str(document_id))
    await db.delete(doc)
    await db.commit()


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

async def _get_or_404(db: AsyncSession, document_id: int) -> Document:
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan.")
    return doc


async def _audit(db, user_id, action, resource_id):
    from app.models.audit import AuditLog
    db.add(AuditLog(
        user_id=user_id, action=action,
        resource_type="document", resource_id=resource_id,
        status="SUCCESS",
    ))
    await db.commit()
