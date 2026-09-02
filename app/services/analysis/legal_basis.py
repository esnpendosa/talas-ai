"""
TALAS AI — Legal Basis Checker (Phase 9)
Periksa dasar hukum setiap pasal dalam regulasi/raperbup.

PRINSIP:
- Setiap pasal harus memiliki dasar hukum yang dapat dilacak
- Status: FOUND | NOT_FOUND | NEEDS_REVIEW (tidak ada LEGAL/ILLEGAL)
- Disclaimer wajib muncul di setiap output
- AI hanya co-pilot, bukan pengambil keputusan
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import Analysis, AnalysisFinding, AnalysisSource
from app.models.document import DocumentChunk, Document
from app.prompts.system import LEGAL_BASIS_PROMPT_TEMPLATE, MAIN_SYSTEM_PROMPT
from app.services.ai.base import ChatMessage
from app.services.ai.router import get_ai_router
from app.services.rag.search import keyword_search

logger = logging.getLogger("talas_ai.analysis.legal_basis")

DISCLAIMER = "TINJAUAN AWAL AI — WAJIB VERIFIKASI MANUSIA."


async def check_legal_basis(
    db: AsyncSession,
    regulation_id: int,
    analysis_id: int,
) -> int:
    """
    Periksa dasar hukum untuk setiap pasal dalam regulasi.
    Untuk setiap DocumentChunk dengan nilai pasal, gunakan RAG untuk mencari
    regulasi pendukung.

    Returns: jumlah finding yang dihasilkan
    """
    # Ambil semua chunk dengan pasal dari regulasi ini
    stmt = (
        select(DocumentChunk)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(Document.regulation_id == regulation_id)
        .where(DocumentChunk.pasal.isnot(None))
        .where(DocumentChunk.pasal != "")
    )
    result = await db.execute(stmt)
    chunks = result.scalars().all()

    if not chunks:
        # Tidak ada pasal — buat satu finding NOT_FOUND
        finding = AnalysisFinding(
            analysis_id=analysis_id,
            pasal=None,
            finding_type="LEGAL_BASIS",
            status="NOT_FOUND",
            confidence=0.0,
            finding=f"{DISCLAIMER}\n\nTidak ditemukan pasal dalam dokumen regulasi ini.",
            analysis_text="Dokumen tidak memiliki struktur pasal yang dapat dianalisis.",
            recommendation="Pastikan dokumen sudah diproses dan memiliki teks yang terstruktur.",
            review_status="AI_GENERATED",
        )
        db.add(finding)
        await db.commit()
        return 1

    finding_count = 0
    router = get_ai_router()

    for chunk in chunks:
        try:
            # Cari regulasi pendukung via keyword search
            query = f"{chunk.pasal} {chunk.text[:200]}"
            hits = await keyword_search(db, query, limit=5)

            # Filter: hanya regulasi bukan dari regulation_id yang sama
            supporting_hits = [
                h for h in hits
                if h.regulation_id != regulation_id
            ]

            # Tentukan status awal berdasarkan evidence
            if len(supporting_hits) >= 2:
                initial_status = "FOUND"
                confidence = min(0.9, 0.5 + len(supporting_hits) * 0.1)
            elif len(supporting_hits) == 1:
                initial_status = "NEEDS_REVIEW"
                confidence = 0.5
            else:
                initial_status = "NOT_FOUND"
                confidence = 0.1

            # Build evidence text untuk prompt
            evidence_parts = []
            for i, hit in enumerate(supporting_hits[:3], 1):
                reg_info = f"{hit.regulation_jenis or ''} No. {hit.regulation_nomor or '?'} Tahun {hit.regulation_tahun or '?'}"
                if hit.pasal:
                    reg_info += f" {hit.pasal}"
                evidence_parts.append(f"[Evidence {i}] {reg_info}\n{hit.excerpt}")

            evidence_text = "\n\n".join(evidence_parts) if evidence_parts else "Tidak ada evidence ditemukan."

            # Panggil LLM via AI Router
            prompt = LEGAL_BASIS_PROMPT_TEMPLATE.format(
                article_text=chunk.text[:500],
                pasal_ref=chunk.pasal or "Pasal tidak teridentifikasi",
                evidence=evidence_text,
            )
            messages = [
                ChatMessage(role="system", content=MAIN_SYSTEM_PROMPT),
                ChatMessage(role="user", content=prompt),
            ]
            llm_result = await router.run_chat(messages, task_name="legal_basis")

            ai_text = llm_result.content or ""
            if not ai_text.startswith(DISCLAIMER):
                ai_text = f"{DISCLAIMER}\n\n{ai_text}"

            # Refine status berdasarkan AI response
            final_status = _parse_status_from_response(ai_text, initial_status)

            # Buat finding
            finding = AnalysisFinding(
                analysis_id=analysis_id,
                pasal=chunk.pasal,
                ayat=chunk.ayat,
                finding_type="LEGAL_BASIS",
                status=final_status,
                confidence=confidence,
                finding=ai_text[:2000] if ai_text else f"{DISCLAIMER}\n\nAnalisis dasar hukum {chunk.pasal}.",
                analysis_text=f"Evidence ditemukan: {len(supporting_hits)} regulasi pendukung.",
                recommendation=_generate_recommendation(final_status, chunk.pasal),
                review_status="AI_GENERATED",
            )
            db.add(finding)
            await db.flush()

            # Tambah sources
            for hit in supporting_hits[:3]:
                source = AnalysisSource(
                    finding_id=finding.id,
                    chunk_id=hit.chunk_id,
                    regulation_name=hit.regulation_judul or "Regulasi tidak teridentifikasi",
                    regulation_number=hit.regulation_nomor,
                    regulation_year=hit.regulation_tahun,
                    pasal=hit.pasal,
                    excerpt=hit.excerpt[:500] if hit.excerpt else None,
                    similarity_score=hit.score,
                )
                db.add(source)

            finding_count += 1

        except Exception as e:
            logger.error(f"Error checking legal basis for pasal {chunk.pasal}: {e}")
            # Buat finding NEEDS_REVIEW jika terjadi error
            finding = AnalysisFinding(
                analysis_id=analysis_id,
                pasal=chunk.pasal,
                finding_type="LEGAL_BASIS",
                status="NEEDS_REVIEW",
                confidence=0.0,
                finding=f"{DISCLAIMER}\n\nTerjadi kesalahan saat menganalisis. Verifikasi manual diperlukan.",
                analysis_text=f"Error: {str(e)[:200]}",
                recommendation="Lakukan verifikasi manual terhadap dasar hukum pasal ini.",
                review_status="AI_GENERATED",
            )
            db.add(finding)
            finding_count += 1

    await db.commit()
    logger.info(f"Legal basis check complete: {finding_count} findings for regulation {regulation_id}")
    return finding_count


def _parse_status_from_response(ai_text: str, default: str) -> str:
    """Parse status dari respons AI. Fallback ke default jika tidak ditemukan."""
    ai_upper = ai_text.upper()
    if "NOT_FOUND" in ai_upper or "TIDAK DITEMUKAN" in ai_upper:
        return "NOT_FOUND"
    if "FOUND" in ai_upper or "DITEMUKAN" in ai_upper:
        return "FOUND"
    if "NEEDS_REVIEW" in ai_upper or "PERLU REVIEW" in ai_upper:
        return "NEEDS_REVIEW"
    return default


def _generate_recommendation(status: str, pasal: Optional[str]) -> str:
    """Generate rekomendasi berdasarkan status finding."""
    ref = pasal or "Pasal ini"
    if status == "FOUND":
        return f"{ref}: Dasar hukum ditemukan. Verifikasi kesesuaian dengan peraturan yang berlaku."
    elif status == "NOT_FOUND":
        return f"{ref}: Dasar hukum tidak ditemukan dalam database. Perlu penambahan dasar hukum yang relevan."
    else:
        return f"{ref}: Memerlukan verifikasi lebih lanjut oleh analis hukum. Evidence yang ada belum cukup."
