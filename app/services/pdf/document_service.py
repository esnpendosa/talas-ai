"""
TALAS AI — Document Service
Upload, validasi, simpan, dan proses dokumen.
Path traversal protection wajib diterapkan.
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.document import Document, DocumentChunk
from app.services.pdf.extractor import extract_pdf, parse_regulation_structure

logger = logging.getLogger("talas_ai.pdf")

ALLOWED_MIME = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "doc": "application/msword",
}


def _safe_filename(original: str) -> str:
    """
    Buat nama file yang aman — gunakan UUID, abaikan nama asli untuk path.
    Cegah path traversal.
    """
    ext = Path(original).suffix.lower().lstrip(".")
    if ext not in settings.allowed_extensions_list:
        ext = "bin"
    return f"{uuid.uuid4().hex}.{ext}"


def _validate_upload(filename: str, size: int) -> Tuple[bool, str]:
    """Validasi file sebelum disimpan."""
    ext = Path(filename).suffix.lower().lstrip(".")
    if ext not in settings.allowed_extensions_list:
        return False, f"Tipe file tidak diizinkan: .{ext}"
    if size > settings.max_upload_bytes:
        return False, f"Ukuran file melebihi batas {settings.MAX_UPLOAD_SIZE_MB} MB."
    if size == 0:
        return False, "File kosong."
    return True, ""


async def save_uploaded_file(
    db: AsyncSession,
    file_content: bytes,
    original_filename: str,
    regulation_id: Optional[int],
    uploaded_by: int,
) -> Document:
    """
    Simpan file ke disk dengan nama aman (UUID).
    Cek duplikasi via SHA-256 hash.
    """
    import hashlib

    # Validasi
    ok, msg = _validate_upload(original_filename, len(file_content))
    if not ok:
        raise ValueError(msg)

    # Hitung hash
    file_hash = hashlib.sha256(file_content).hexdigest()

    # Cek duplikasi
    existing = await db.execute(
        select(Document).where(Document.file_hash == file_hash)
    )
    dup = existing.scalar_one_or_none()
    if dup:
        logger.info(f"Duplicate file detected: {original_filename} -> {dup.id}")
        return dup  # Return dokumen yang sudah ada

    # Simpan file dengan nama aman
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    stored_name = _safe_filename(original_filename)
    file_path = upload_dir / stored_name

    # Pastikan tidak ada path traversal
    resolved = file_path.resolve()
    if not str(resolved).startswith(str(upload_dir.resolve())):
        raise ValueError("Path traversal terdeteksi.")

    file_path.write_bytes(file_content)

    ext = Path(original_filename).suffix.lower().lstrip(".")
    doc = Document(
        regulation_id=regulation_id,
        original_filename=original_filename,
        stored_filename=stored_name,
        file_path=str(file_path),
        file_size=len(file_content),
        file_type=ext,
        file_hash=file_hash,
        processing_status="PENDING",
        uploaded_by=uploaded_by,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


async def process_document(db: AsyncSession, document_id: int) -> Document:
    """
    Proses dokumen: ekstrak teks, parse struktur regulasi, buat chunks.
    Berjalan secara synchronous untuk MVP (background task di phase lanjutan).
    """
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise ValueError(f"Dokumen {document_id} tidak ditemukan.")

    if doc.processing_status == "COMPLETED":
        return doc

    doc.processing_status = "PROCESSING"
    await db.commit()

    try:
        file_path = Path(doc.file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File tidak ditemukan: {doc.file_path}")

        if doc.file_type == "pdf":
            extraction = extract_pdf(file_path, enable_ocr=settings.ENABLE_OCR)

            if not extraction.success:
                doc.processing_status = "FAILED"
                doc.processing_error = extraction.error
                await db.commit()
                return doc

            doc.page_count = extraction.page_count
            doc.extracted_text_length = len(extraction.full_text)
            doc.ocr_used = extraction.ocr_used
            doc.processed_at = datetime.now(timezone.utc)

            # Hapus chunks lama jika re-process
            old_chunks = await db.execute(
                select(DocumentChunk).where(DocumentChunk.document_id == doc.id)
            )
            for chunk in old_chunks.scalars().all():
                await db.delete(chunk)

            # Parse dan simpan chunks
            chunks = parse_regulation_structure(
                extraction.pages,
                chunk_size=settings.CHUNK_SIZE,
                chunk_overlap=settings.CHUNK_OVERLAP,
            )

            for rc in chunks:
                db.add(DocumentChunk(
                    document_id=doc.id,
                    text=rc.text,
                    text_length=len(rc.text),
                    chunk_index=rc.chunk_index,
                    page_start=rc.page_start,
                    page_end=rc.page_end,
                    bab=rc.bab,
                    bagian=rc.bagian,
                    pasal=rc.pasal,
                ))

            doc.processing_status = "COMPLETED"
            if extraction.error:
                doc.processing_error = extraction.error

        else:
            # DOCX — placeholder, akan diimplementasikan dengan python-docx
            doc.processing_status = "FAILED"
            doc.processing_error = "Format DOCX belum didukung di versi ini."

        await db.commit()
        await db.refresh(doc)
        return doc

    except Exception as e:
        logger.error(f"Document processing failed [{document_id}]: {e}")
        doc.processing_status = "FAILED"
        doc.processing_error = "Dokumen tidak dapat diproses."
        await db.commit()
        return doc
