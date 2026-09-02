"""
TALAS AI — Conflict Checker (Phase 10)
Periksa potensi konflik antara Raperbup dan regulasi yang lebih tinggi.

PRINSIP:
- Jangan menyatakan "bertentangan" secara absolut
- Gunakan "berpotensi konflik" atau POTENTIAL_CONFLICT
- Status: NO_ISSUE | DIFFERENCE | POTENTIAL_CONFLICT | NEEDS_REVIEW
- Disclaimer wajib di setiap output
"""
from __future__ import annotations

import logging
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import Analysis, AnalysisFinding, AnalysisSource
from app.models.document import DocumentChunk, Document
from app.models.regulation import Regulation
from app.prompts.system import CONFLICT_CHECK_PROMPT_TEMPLATE, MAIN_SYSTEM_PROMPT
from app.services.ai.base import ChatMessage
from app.services.ai.router import get_ai_router
from app.services.rag.search import keyword_search

logger = logging.getLogger("talas_ai.analysis.conflict")

DISCLAIMER = "TINJAUAN AWAL AI — WAJIB VERIFIKASI MANUSIA."


async def check_conflicts(
    db: AsyncSession,
    regulation_id: int,
    analysis_id: int,
) -> int:
    """
    Periksa potensi konflik antara regulasi (Raperbup) dan regulasi lain.
    Bandingkan ketentuan dengan UU, PP, Perpres, Permen, Permendagri, Perda.

    Returns: jumlah finding yang dihasilkan
    """
    # Ambil chunks dari regulasi yang dianalisis
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
        finding = AnalysisFinding(
            analysis_id=analysis_id,
            pasal=None,
            finding_type="CONFLICT",
            status="NEEDS_REVIEW",
            confidence=0.0,
            finding=f"{DISCLAIMER}\n\nTidak ditemukan pasal untuk diperiksa konfliknya.",
            analysis_text="Dokumen tidak memiliki struktur pasal yang dapat dianalisis.",
            recommendation="Pastikan dokumen sudah diproses dengan benar.",
            review_status="AI_GENERATED",
        )
        db.add(finding)
        await db.commit()
        return 1

    router = get_ai_router()
    finding_count = 0

    for chunk in chunks:
        try:
            # Cari regulasi yang mungkin konflik (level lebih tinggi)
            query = f"{chunk.pasal} {chunk.text[:200]}"
            hits = await keyword_search(db, query, limit=5)

            # Filter: regulasi lain (bukan regulation_id yang sama)
            other_hits = [h for h in hits if h.regulation_id != regulation_id]

            # Build comparison text
            comparison_parts = []
            for i, hit in enumerate(other_hits[:3], 1):
                reg_info = f"{hit.regulation_jenis or 'Regulasi'} No. {hit.regulation_nomor or '?'} Tahun {hit.regulation_tahun or '?'}"
                if hit.pasal:
                    reg_info += f" {hit.pasal}"
                comparison_parts.append(f"[Regulasi {i}] {reg_info}\n{hit.excerpt}")

            comparison_text = "\n\n".join(comparison_parts) if comparison_parts else "Tidak ada regulasi pembanding ditemukan."

            # Panggil LLM via AI Router
            prompt = CONFLICT_CHECK_PROMPT_TEMPLATE.format(
                raperbup_text=chunk.text[:500],
                pasal_ref=chunk.pasal or "Pasal tidak teridentifikasi",
                comparison_regulations=comparison_text,
            )
            messages = [
                ChatMessage(role="system", content=MAIN_SYSTEM_PROMPT),
                ChatMessage(role="user", content=prompt),
            ]
            llm_result = await router.run_chat(messages, task_name="conflict_check")

            ai_text = llm_result.content or ""
            if not ai_text.startswith(DISCLAIMER):
                ai_text = f"{DISCLAIMER}\n\n{ai_text}"

            # Parse status dari respons
            status = _parse_conflict_status(ai_text, other_hits)

            # Confidence berdasarkan jumlah evidence
            confidence = min(0.85, 0.3 + len(other_hits) * 0.15)

            finding = AnalysisFinding(
                analysis_id=analysis_id,
                pasal=chunk.pasal,
                ayat=chunk.ayat,
                finding_type="CONFLICT",
                status=status,
                confidence=confidence,
                finding=ai_text[:2000],
                analysis_text=f"Dibandingkan dengan {len(other_hits)} regulasi lain.",
                recommendation=_generate_conflict_recommendation(status, chunk.pasal),
                review_status="AI_GENERATED",
            )
            db.add(finding)
            await db.flush()

            # Tambah sources
            for hit in other_hits[:3]:
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
            logger.error(f"Error checking conflict for pasal {chunk.pasal}: {e}")
            finding = AnalysisFinding(
                analysis_id=analysis_id,
                pasal=chunk.pasal,
                finding_type="CONFLICT",
                status="NEEDS_REVIEW",
                confidence=0.0,
                finding=f"{DISCLAIMER}\n\nTerjadi kesalahan saat memeriksa konflik. Verifikasi manual diperlukan.",
                analysis_text=f"Error: {str(e)[:200]}",
                recommendation="Lakukan verifikasi manual terhadap potensi konflik pasal ini.",
                review_status="AI_GENERATED",
            )
            db.add(finding)
            finding_count += 1

    await db.commit()
    logger.info(f"Conflict check complete: {finding_count} findings for regulation {regulation_id}")
    return finding_count


def _parse_conflict_status(ai_text: str, hits: list) -> str:
    """Parse status konflik dari respons AI."""
    ai_upper = ai_text.upper()
    if "POTENTIAL_CONFLICT" in ai_upper or "BERPOTENSI KONFLIK" in ai_upper:
        return "POTENTIAL_CONFLICT"
    if "DIFFERENCE" in ai_upper or "PERBEDAAN" in ai_upper:
        return "DIFFERENCE"
    if "NO_ISSUE" in ai_upper or "TIDAK ADA MASALAH" in ai_upper:
        return "NO_ISSUE"
    if "NEEDS_REVIEW" in ai_upper or "PERLU REVIEW" in ai_upper:
        return "NEEDS_REVIEW"
    # Default berdasarkan jumlah evidence
    if not hits:
        return "NO_ISSUE"
    return "NEEDS_REVIEW"


def _generate_conflict_recommendation(status: str, pasal: str) -> str:
    """Generate rekomendasi berdasarkan status konflik."""
    ref = pasal or "Pasal ini"
    if status == "NO_ISSUE":
        return f"{ref}: Tidak ditemukan indikasi konflik. Tetap lakukan verifikasi final."
    elif status == "DIFFERENCE":
        return f"{ref}: Terdapat perbedaan dengan regulasi lain. Perlu harmonisasi ketentuan."
    elif status == "POTENTIAL_CONFLICT":
        return f"{ref}: PERHATIAN — berpotensi konflik dengan regulasi yang lebih tinggi. Wajib diverifikasi oleh analis hukum."
    else:
        return f"{ref}: Memerlukan telaah lebih lanjut oleh analis hukum berwenang."
