"""
TALAS AI — Consistency Checker (Phase 11)
Periksa konsistensi internal regulasi: istilah, definisi, cross-reference.

PRINSIP:
- Cari ketidakkonsistenan penggunaan istilah yang sama di pasal berbeda
- Status: NO_ISSUE | DIFFERENCE | NEEDS_REVIEW
- Disclaimer wajib di setiap output
"""
from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Dict, List, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import AnalysisFinding, AnalysisSource
from app.models.document import DocumentChunk, Document
from app.prompts.system import CONSISTENCY_CHECK_PROMPT_TEMPLATE, MAIN_SYSTEM_PROMPT
from app.services.ai.base import ChatMessage
from app.services.ai.router import get_ai_router

logger = logging.getLogger("talas_ai.analysis.consistency")

DISCLAIMER = "TINJAUAN AWAL AI — WAJIB VERIFIKASI MANUSIA."


async def check_consistency(
    db: AsyncSession,
    regulation_id: int,
    analysis_id: int,
) -> int:
    """
    Periksa konsistensi internal dokumen regulasi.
    Cek: istilah, definisi, cross-reference, penomoran.

    Returns: jumlah finding yang dihasilkan
    """
    # Ambil semua chunk dari regulasi ini
    stmt = (
        select(DocumentChunk)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(Document.regulation_id == regulation_id)
        .order_by(DocumentChunk.chunk_index)
    )
    result = await db.execute(stmt)
    chunks = result.scalars().all()

    if not chunks:
        finding = AnalysisFinding(
            analysis_id=analysis_id,
            pasal=None,
            finding_type="CONSISTENCY",
            status="NEEDS_REVIEW",
            confidence=0.0,
            finding=f"{DISCLAIMER}\n\nTidak ditemukan konten dokumen untuk diperiksa konsistensinya.",
            analysis_text="Dokumen tidak memiliki konten yang dapat dianalisis.",
            recommendation="Pastikan dokumen sudah diproses dan memiliki teks yang dapat diekstrak.",
            review_status="AI_GENERATED",
        )
        db.add(finding)
        await db.commit()
        return 1

    router = get_ai_router()
    finding_count = 0

    # Gabungkan teks semua chunk untuk analisis konsistensi
    all_text = "\n\n".join(
        f"{chunk.pasal or ''}\n{chunk.text[:300]}"
        for chunk in chunks[:20]  # Batasi 20 chunk untuk efisiensi
    )

    # Deteksi ketidakkonsistenan berbasis teks
    inconsistencies = _detect_term_inconsistencies(chunks)

    try:
        # Panggil LLM untuk analisis komprehensif
        prompt = CONSISTENCY_CHECK_PROMPT_TEMPLATE.format(
            regulation_text=all_text[:3000],
        )
        messages = [
            ChatMessage(role="system", content=MAIN_SYSTEM_PROMPT),
            ChatMessage(role="user", content=prompt),
        ]
        llm_result = await router.run_chat(messages, task_name="consistency_check")

        ai_text = llm_result.content or ""
        if not ai_text.startswith(DISCLAIMER):
            ai_text = f"{DISCLAIMER}\n\n{ai_text}"

        # Buat finding utama dari LLM
        main_status = _parse_consistency_status(ai_text, inconsistencies)

        finding = AnalysisFinding(
            analysis_id=analysis_id,
            pasal=None,
            finding_type="CONSISTENCY",
            status=main_status,
            confidence=0.7 if main_status == "NO_ISSUE" else 0.6,
            finding=ai_text[:2000],
            analysis_text=f"Diperiksa {len(chunks)} bagian. {len(inconsistencies)} potensi ketidakkonsistenan terdeteksi.",
            recommendation=_generate_consistency_recommendation(main_status, inconsistencies),
            review_status="AI_GENERATED",
        )
        db.add(finding)
        await db.flush()
        finding_count += 1

    except Exception as e:
        logger.error(f"Error in LLM consistency check: {e}")
        finding = AnalysisFinding(
            analysis_id=analysis_id,
            pasal=None,
            finding_type="CONSISTENCY",
            status="NEEDS_REVIEW",
            confidence=0.0,
            finding=f"{DISCLAIMER}\n\nTerjadi kesalahan saat analisis AI. Verifikasi manual diperlukan.",
            analysis_text=f"Error: {str(e)[:200]}",
            recommendation="Lakukan review manual terhadap konsistensi dokumen.",
            review_status="AI_GENERATED",
        )
        db.add(finding)
        finding_count += 1

    # Buat finding terpisah untuk setiap ketidakkonsistenan terdeteksi
    for term, pasals in list(inconsistencies.items())[:5]:  # Batasi 5
        detail = f"{DISCLAIMER}\n\nIstilah '{term}' digunakan secara tidak konsisten di: {', '.join(pasals[:3])}"
        finding = AnalysisFinding(
            analysis_id=analysis_id,
            pasal=pasals[0] if pasals else None,
            finding_type="CONSISTENCY",
            status="DIFFERENCE",
            confidence=0.65,
            finding=detail,
            analysis_text=f"Istilah '{term}' muncul di {len(pasals)} pasal dengan variasi penulisan.",
            recommendation=f"Harmonisasikan penggunaan istilah '{term}' di seluruh dokumen.",
            review_status="AI_GENERATED",
        )
        db.add(finding)
        finding_count += 1

    await db.commit()
    logger.info(f"Consistency check complete: {finding_count} findings for regulation {regulation_id}")
    return finding_count


def _detect_term_inconsistencies(chunks: list) -> Dict[str, List[str]]:
    """
    Deteksi ketidakkonsistenan istilah berbasis teks sederhana.
    Cari variasi penulisan yang mungkin merujuk hal sama.
    """
    # Pola variasi umum dalam regulasi Indonesia
    variant_patterns = [
        (r"\bpemerintah daerah\b", r"\bpemda\b"),
        (r"\bperaturan bupati\b", r"\bperbup\b"),
        (r"\borganisasi perangkat daerah\b", r"\bopd\b"),
        (r"\banggaran pendapatan\b", r"\bapbd\b"),
    ]

    inconsistencies: Dict[str, List[str]] = defaultdict(list)

    for chunk in chunks:
        text_lower = chunk.text.lower()
        pasal = chunk.pasal or f"chunk_{chunk.id}"

        for pattern_a, pattern_b in variant_patterns:
            has_a = bool(re.search(pattern_a, text_lower))
            has_b = bool(re.search(pattern_b, text_lower))
            if has_a and has_b:
                key = pattern_a.replace(r"\b", "").strip()
                if pasal not in inconsistencies[key]:
                    inconsistencies[key].append(pasal)

    return dict(inconsistencies)


def _parse_consistency_status(ai_text: str, inconsistencies: dict) -> str:
    """Parse status konsistensi."""
    ai_upper = ai_text.upper()
    if "DIFFERENCE" in ai_upper or "TIDAK KONSISTEN" in ai_upper or "INKONSISTEN" in ai_upper:
        return "DIFFERENCE"
    if "NEEDS_REVIEW" in ai_upper or "PERLU REVIEW" in ai_upper:
        return "NEEDS_REVIEW"
    if "NO_ISSUE" in ai_upper or "KONSISTEN" in ai_upper:
        return "NO_ISSUE"
    return "NEEDS_REVIEW" if inconsistencies else "NO_ISSUE"


def _generate_consistency_recommendation(status: str, inconsistencies: dict) -> str:
    """Generate rekomendasi konsistensi."""
    if status == "NO_ISSUE":
        return "Dokumen menunjukkan konsistensi yang baik. Verifikasi final tetap diperlukan."
    elif status == "DIFFERENCE":
        terms = list(inconsistencies.keys())[:3]
        if terms:
            return f"Harmonisasikan penggunaan istilah: {', '.join(terms)}. Buat glosarium standar."
        return "Perbaiki ketidakkonsistenan istilah dan definisi dalam dokumen."
    else:
        return "Lakukan review manual komprehensif terhadap konsistensi seluruh dokumen."
