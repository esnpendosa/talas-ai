"""
TALAS AI — Comparison Engine (Phase 12)
Bandingkan dua regulasi pasal per pasal.

PRINSIP:
- Kategorisasi: UNCHANGED | CHANGED | ADDED | REMOVED | NEEDS_REVIEW
- Disclaimer wajib di setiap output
- Tidak menyatakan satu regulasi lebih baik dari yang lain secara mutlak
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import DocumentChunk, Document

logger = logging.getLogger("talas_ai.analysis.comparison")

DISCLAIMER = "TINJAUAN AWAL AI — WAJIB VERIFIKASI MANUSIA."


async def compare_regulations(
    db: AsyncSession,
    regulation_id_a: int,
    regulation_id_b: int,
) -> Dict:
    """
    Bandingkan dua regulasi pasal per pasal.

    Returns: dict dengan hasil perbandingan
    """
    # Ambil chunks dari regulasi A
    chunks_a = await _get_regulation_chunks(db, regulation_id_a)
    # Ambil chunks dari regulasi B
    chunks_b = await _get_regulation_chunks(db, regulation_id_b)

    # Index berdasarkan pasal
    pasal_map_a: Dict[str, str] = {}
    for chunk in chunks_a:
        if chunk.pasal:
            existing = pasal_map_a.get(chunk.pasal, "")
            pasal_map_a[chunk.pasal] = (existing + " " + chunk.text).strip()

    pasal_map_b: Dict[str, str] = {}
    for chunk in chunks_b:
        if chunk.pasal:
            existing = pasal_map_b.get(chunk.pasal, "")
            pasal_map_b[chunk.pasal] = (existing + " " + chunk.text).strip()

    all_pasals = set(pasal_map_a.keys()) | set(pasal_map_b.keys())

    comparison_results = []
    stats = {
        "UNCHANGED": 0,
        "CHANGED": 0,
        "ADDED": 0,
        "REMOVED": 0,
        "NEEDS_REVIEW": 0,
    }

    for pasal in sorted(all_pasals):
        text_a = pasal_map_a.get(pasal)
        text_b = pasal_map_b.get(pasal)

        category, notes = _compare_pasal(pasal, text_a, text_b)
        stats[category] = stats.get(category, 0) + 1

        comparison_results.append({
            "pasal": pasal,
            "category": category,
            "text_a": text_a[:500] if text_a else None,
            "text_b": text_b[:500] if text_b else None,
            "notes": notes,
        })

    return {
        "disclaimer": DISCLAIMER,
        "regulation_id_a": regulation_id_a,
        "regulation_id_b": regulation_id_b,
        "total_pasals": len(all_pasals),
        "stats": stats,
        "results": comparison_results,
        "summary": _build_comparison_summary(stats, len(all_pasals)),
    }


async def _get_regulation_chunks(
    db: AsyncSession,
    regulation_id: int,
) -> List[DocumentChunk]:
    """Ambil semua DocumentChunk untuk sebuah regulasi."""
    stmt = (
        select(DocumentChunk)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(Document.regulation_id == regulation_id)
        .order_by(DocumentChunk.chunk_index)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


def _compare_pasal(
    pasal: str,
    text_a: Optional[str],
    text_b: Optional[str],
) -> Tuple[str, str]:
    """
    Bandingkan teks pasal dari dua regulasi.

    Returns: (category, notes)
    """
    if text_a is None and text_b is not None:
        return "ADDED", f"{pasal} hanya ada di regulasi B (baru ditambahkan)."
    elif text_a is not None and text_b is None:
        return "REMOVED", f"{pasal} hanya ada di regulasi A (dihapus di regulasi B)."
    elif text_a is None and text_b is None:
        return "NEEDS_REVIEW", f"{pasal} tidak ditemukan teksnya di kedua regulasi."

    # Kedua ada — bandingkan similarity
    similarity = _text_similarity(text_a, text_b)

    if similarity >= 0.95:
        return "UNCHANGED", f"{pasal} hampir identik (similarity: {similarity:.0%})."
    elif similarity >= 0.6:
        return "CHANGED", f"{pasal} mengalami perubahan (similarity: {similarity:.0%}). Perlu diverifikasi."
    else:
        return "NEEDS_REVIEW", f"{pasal} sangat berbeda (similarity: {similarity:.0%}). Wajib diverifikasi analis."


def _text_similarity(text_a: str, text_b: str) -> float:
    """
    Hitung similarity sederhana antara dua teks.
    Menggunakan Jaccard similarity berbasis kata.
    """
    if not text_a or not text_b:
        return 0.0

    words_a = set(text_a.lower().split())
    words_b = set(text_b.lower().split())

    if not words_a or not words_b:
        return 0.0

    intersection = len(words_a & words_b)
    union = len(words_a | words_b)

    return intersection / union if union > 0 else 0.0


def _build_comparison_summary(stats: Dict[str, int], total: int) -> str:
    """Build summary teks perbandingan."""
    if total == 0:
        return f"{DISCLAIMER}\n\nTidak ada pasal yang dapat dibandingkan."

    lines = [
        DISCLAIMER,
        "",
        f"Hasil perbandingan terhadap {total} pasal:",
        f"- Tidak berubah (UNCHANGED): {stats.get('UNCHANGED', 0)} pasal",
        f"- Berubah (CHANGED): {stats.get('CHANGED', 0)} pasal",
        f"- Ditambahkan (ADDED): {stats.get('ADDED', 0)} pasal",
        f"- Dihapus (REMOVED): {stats.get('REMOVED', 0)} pasal",
        f"- Perlu review (NEEDS_REVIEW): {stats.get('NEEDS_REVIEW', 0)} pasal",
        "",
        "Catatan: Perbandingan ini adalah analisis awal berbasis teks. "
        "Verifikasi manual oleh analis hukum tetap diperlukan.",
    ]
    return "\n".join(lines)
